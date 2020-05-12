
import os
import psutil
import logging as log
from typing import List
from xml.etree.ElementTree import iterparse

from icarus.parse.events.node import Node
from icarus.parse.events.link import Link
from icarus.parse.events.route import Route
from icarus.parse.events.types import NetworkMode, LegMode
from icarus.parse.events.agent import Agent
from icarus.util.sqlite import SqliteUtil
from icarus.util.general import counter, defaultdict
from icarus.util.file import multiopen


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
        nodes = counter(self.fetch_nodes(), 'Loading node %s.')
        for node in nodes:
            node_id = node[0]
            maz = node[1]
            x, y = xy(node[2])
            self.nodes[node_id] = Node(node_id, maz, x, y)


    def load_links(self):
        log.info('Fetching network road link data.')
        links = counter(self.fetch_links(), 'Loading link %s.')
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
        plansfile = multiopen(planspath, mode='rb')
        plans = iter(iterparse(plansfile, events=('start', 'end')))
        evt, root = next(plans)

        agent = None
        selected = False
        mode = None
        count = 0
        n = 1

        log.info('Fetching output plans routing data.')
        for evt, elem in plans:
            if evt == 'start':
                if elem.tag == 'person':
                    agent = elem.get('id')
                elif elem.tag == 'plan':
                    selected = elem.get('selected') == 'yes'
                elif elem.tag == 'leg':
                    mode = elem.get('mode')
            elif evt == 'end':
                if elem.tag == 'route' and selected:
                    vehicle = elem.get('vehicleRefId')
                    kind = elem.get('type')
                    if vehicle == 'null' and kind == 'links':
                        start = elem.get('start_link')
                        end = elem.get('end_link')
                        distance = float(elem.get('distance'))
                        path = (self.links[link] for link in elem.text.split(' '))
                        uuid = f'{mode}-{start}-{end}'
                        route = Route(self.links[start], self.links[end], 
                            tuple(path), distance, LegMode(mode))
                        self.agents[agent].routes[uuid] = route
                elif elem.tag == 'person':
                    count += 1
                    if count % 10000 == 0:
                        root.clear()
                    if count == n:
                        log.info(f'Processing route {count}.')
                        n <<= 1

        if count != (n >> 1):
            log.info(f'Processing route {count}.')
        plansfile.close()

        self.agents.lock()

    
    def load_network(self, planspath: str):
        log.info('Loading network data.')
        self.load_nodes()
        self.load_links()
        self.load_routes(planspath)

