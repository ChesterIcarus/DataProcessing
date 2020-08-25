
import os
import logging as log

from typing import List
from multiprocessing import Pool, Value
from xml.etree.ElementTree import iterparse, XMLPullParser

from icarus.parse.events.node import Node
from icarus.parse.events.link import Link
from icarus.parse.events.route import Route
from icarus.parse.events.types import NetworkMode, LegMode
from icarus.parse.events.agent import Agent
from icarus.util.sqlite import SqliteUtil
from icarus.util.general import counter, defaultdict
from icarus.util.file import multiopen


total: Value = None

def load_routes_thread(filename: str, offset: int, chunk_size: int):
    # open the xml and move to assigned offset

    xmlfile = open(filename, 'r')
    xmlfile.seek(offset)

    # define file block reading behavior

    block_last = offset + chunk_size
    block_size = 1024 * 1024
    block_iter = iter(range(offset, block_last, block_size))
    block_get = lambda: (xmlfile.read(block_size), next(block_iter, None))
    data, block = '',  -1

    # intialize parser; insert fake root

    parser = XMLPullParser(events=('start', 'end'))
    parser.feed('<population>')    
    evt, elem = next(parser.read_events())
    root = elem

    # scan to find valid start location

    idx = -1
    scan = block is not None
    while idx < 0 and scan:
        data, block = block_get()
        scan = block is not None
        idx = data.find('<person')    
    data = data[idx:]

    # begin iteration process

    count = 0
    routes = []
    scan = block is not None
    while scan:
        parser.feed(data)
        for evt, elem in parser.read_events():
            if evt == 'start':
                if elem.tag == 'person':
                    agent = elem.get('id')
                    if block is None:
                        scan = False
                        break
                elif elem.tag == 'plan':
                    selected = elem.get('selected') == 'yes'
                elif elem.tag == 'leg':
                    mode = elem.get('mode')
            elif evt == 'end':
                if elem.tag == 'route' and selected:
                    vehicle = elem.get('vehicleRefId')
                    kind = elem.get('type')
                    if vehicle == 'null' and kind == 'links':
                        dist = float(elem.get('distance'))
                        path = elem.text.split(' ')
                        routes.append((agent, mode, dist, path))
                elif elem.tag == 'person':
                    count += 1
                    if count % 1000 == 0:
                        root.clear()
                elif elem.tag == 'population':
                    scan = False
                    break
        if scan:
            data, block = block_get()
    
    xmlfile.close()

    global total
    num = len(routes)
    with total.get_lock():
        total.value += num
        log.debug(f'Proccessing route {total.value}.')

    return routes


def xy(point: str) -> tuple:
    return tuple(map(float, point[7:-1].split(' ')))


class Network:
    __slots__ = ('database', 'nodes', 'links', 'routes', 'agents')

    def __init__(self, database: 'SqliteUtil'):
        self.database = database
        self.links = {}
        self.nodes = {}
        self.agents = defaultdict(lambda uuid: Agent(uuid))

    
    def fetch_nodes(self) -> List[List]:
        self.database.cursor.execute('''
            SELECT
                node_id,
                maz,
                point
            FROM nodes; ''')
        return self.database.cursor.fetchall()


    def fetch_links(self) -> List[List]:
        self.database.cursor.execute('''
            SELECT
                link_id,
                source_node,
                terminal_node,
                length,
                freespeed,
                modes
            FROM links; ''')
        return self.database.cursor.fetchall()


    def load_nodes(self):
        log.info('Loading network road node data.')
        nodes = counter(self.fetch_nodes(), 'Loading node %s.', level=log.DEBUG)
        for node in nodes:
            node_id = node[0]
            maz = node[1]
            x, y = xy(node[2])
            self.nodes[node_id] = Node(node_id, maz, x, y)


    def load_links(self):
        log.info('Fetching network road link data.')
        links = counter(self.fetch_links(), 'Loading link %s.', level=log.DEBUG)
        for link in links:
            link_id = link[0]
            src_node = self.nodes[link[1]]
            term_node = self.nodes[link[2]]
            length = link[3]
            freespeed = link[4]
            modes = set(NetworkMode(mode) for mode in link[5].split(','))
            self.links[link_id] = Link(link_id, src_node, term_node, 
                length, freespeed, modes)


    def load_routes(self, planspath: str):
        log.info('Fetching output plans routing data.')

        global total
        total = Value('I', 0)

        total_size = os.path.getsize(planspath)
        chunk_size = 1024 * 1024 * 1024 // 2
        offsets = range(0, total_size, chunk_size)
        args = ((planspath, offset, chunk_size) for offset in offsets)

        log.debug('Splitting task for multicore processing.')

        with Pool() as pool:
            routes = pool.starmap(load_routes_thread, args)

        routes = [r for route in routes for r in route]

        log.debug('Merging threads and cleaning up.')

        for agent, mode, dist, path in routes:
            links = tuple(self.links[link] for link in path)
            route = Route(links, dist, LegMode(mode))
            self.agents[agent].routes.append(route)

        self.agents.lock()

        del routes

        
    # def load_routes(self, planspath: str):
    #     plansfile = multiopen(planspath, mode='rb')
    #     plans = iter(iterparse(plansfile, events=('start', 'end')))
    #     evt, root = next(plans)

    #     agent = None
    #     selected = False
    #     mode = None
    #     count = 0
    #     n = 1

    #     log.info('Fetching output plans routing data.')
    #     for evt, elem in plans:
    #         if evt == 'start':
    #             if elem.tag == 'person':
    #                 agent = elem.get('id')
    #             elif elem.tag == 'plan':
    #                 selected = elem.get('selected') == 'yes'
    #             elif elem.tag == 'leg':
    #                 mode = elem.get('mode')
    #         elif evt == 'end':
    #             if elem.tag == 'route' and selected:
    #                 vehicle = elem.get('vehicleRefId')
    #                 kind = elem.get('type')
    #                 if vehicle == 'null' and kind == 'links':
    #                     start = elem.get('start_link')
    #                     end = elem.get('end_link')
    #                     distance = float(elem.get('distance'))
    #                     path = (self.links[link] for link in elem.text.split(' '))
    #                     uuid = f'{mode}-{start}-{end}'
    #                     route = Route(self.links[start], self.links[end], 
    #                         tuple(path), distance, LegMode(mode))
    #                     self.agents[agent].routes[uuid] = route
    #             elif elem.tag == 'person':
    #                 count += 1
    #                 if count % 10000 == 0:
    #                     root.clear()
    #                 if count == n:
    #                     log.info(f'Processing route {count}.')
    #                     n <<= 1

    #     if count != (n >> 1):
    #         log.info(f'Processing route {count}.')
    #     plansfile.close()

    #     self.agents.lock()

    
    def load_network(self, planspath: str):
        log.info('Loading network data.')
        self.load_nodes()
        self.load_links()
        self.load_routes(planspath)

