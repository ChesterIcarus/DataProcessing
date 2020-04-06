
import logging as log
from xml.etree.ElementTree import iterparse, tostring
from rtree import index
from icarus.output.objects.types import LegMode
from icarus.output.objects.agent import Agent
from icarus.util.general import defaultdict
from icarus.util.file import multiopen


class Route:
    __slots__= ('start_link', 'end_link', 'path', 'distance', 'mode')

    def __init__(self, start_link, end_link, path, distance, mode):
        self.start_link = start_link
        self.end_link = end_link
        self.path = path
        self.distance = distance
        self.mode = mode

    def get_exposure(self, start, stop):
        exposure = 0
        total = stop - start
        time = start
        distance = sum(link.length for link in self.path)
        for link in self.path:
            elapse = int(total * link.length / distance)
            exposure += link.get_exposure(time, time + elapse)
            time += elapse
        return exposure



class Link:
    __slots__ = ('id', 'x', 'y', 'length', 'freespeed', 'centroid')

    def __init__(self, uuid, x, y, length, freespeed):
        self.id = uuid
        self.x = x
        self.y = y
        self.length = length
        self.freespeed = freespeed
        self.centroid = None
    

    def get_temperature(self, time):
        return self.centroid.get_temperature(time)


    def get_exposure(self, start, stop):
        return self.centroid.get_exposure(start, stop)


    def entry(self):
        return (self.x, self.y, self.x, self.y)



class Centroid:
    steps = None

    def __init__(self, uuid, x, y, temperatures):
        self.id = uuid
        self.x = x
        self.y = y
        self.temperatures = temperatures


    def get_temperature(self, time):
        step = int(time / 86400 * self.steps) % self.steps
        return self.temperatures[step]


    def get_exposure(self, start, stop):
        steps = len(self.temperatures)
        step_size = int(86400 / steps)
        start_step = int(start / 86400 * steps) % steps
        stop_step = int(stop / 86400 * steps) % steps
        exposure = 0
        if start_step == stop_step:
            exposure = (stop - start) * self.temperatures[start_step]
        else:
            exposure = ((start_step + 1) * step_size - start) * \
                self.temperatures[start_step]
            for step in range(start_step + 1, stop_step):
                exposure += step_size * self.temperatures[step]
            exposure += (stop - stop_step * step_size) * self.temperatures[stop_step]
        return exposure

    def entry(self):
        return (self.id, (self.x, self.y, self.x, self.y), None)



class Network:
    def __init__(self, database):
        self.database = database
        self.temperatures = defaultdict(lambda x: [])
        self.routes = []
        self.agents = {}
        self.links = {}
        self.centroids = {}


    def fetch_temperatures(self):
        self.database.cursor.execute('''
            SELECT
                temperature_id,
                temperature_idx,
                temperature
            FROM temperatures
            ORDER BY
                temperature_id,
                temperature_idx;  ''')
        return self.database.cursor.fetchall()


    def fetch_links(self):
        self.database.cursor.execute('''
            SELECT
                links.link_id,
                links.length,
                links.freespeed,
                links.modes,
                nodes.point
            FROM links
            INNER JOIN nodes
            ON links.source_node = nodes.node_id; ''')
        return self.database.cursor.fetchall()

    
    def fetch_centroids(self):
        self.database.cursor.execute('''
            SELECT
                centroid_id,
                temperature_id,
                center
            FROM centroids; ''')
        return self.database.cursor.fetchall()


    def get_agent(self, agent_id):
        agent = None
        if agent_id in self.agents:
            agent = self.agents[agent_id]
        else:
            agent = Agent(agent_id)
            self.agents[agent_id] = Agent(agent_id)
        return agent

    
    def fetch_routes(self, planspath):
        routes = []
        plansfile = multiopen(planspath, mode='rb')
        plans = iter(iterparse(plansfile, events=('start', 'end')))
        evt, root = next(plans)

        agent = None
        selected = False
        mode = None
        count = 0
        n = 0

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
                        path = tuple(self.links[link] for link in elem.text.split(' '))
                        uuid = f'{mode}-{start}-{end}'
                        route = Route(self.links[start], self.links[end], 
                            path, distance, LegMode(mode))
                        self.get_agent(agent).routes[uuid] = route
                        routes.append(route)
                elif elem.tag == 'agent':
                    count += 1
                    if count % 10000 == 0:
                        root.clear()
                    if count == n:
                        log.info(f'Processing plan {count}.')
                        n <<= 1

        if count != (n >> 1):
            log.info(f'Processing plan {count}.')
        plansfile.close()

        return routes

    
    def load_network(self, planspath):
        log.info('Loading network temperatures from database.')
        temperatures = self.fetch_temperatures()
        for temperature in temperatures:
            self.temperatures[temperature[0]].append(temperature[2])
        self.temperatures.lock()
        
        log.info('Loading network centroids from database.')
        centroids = self.fetch_centroids()
        for centroid in centroids:
            uuid = centroid[0]
            x, y = map(float, centroid[2][7:-1].split(' '))
            self.centroids[uuid] = Centroid(uuid, x, y, self.temperatures[centroid[1]])
        Centroid.steps = len(next(iter(self.temperatures.values())))

        log.info('Loading network links from database.')
        links = self.fetch_links()
        for link in links:
            uuid = link[0]
            x, y = map(float, link[4][7:-1].split(' '))
            self.links[uuid] = Link(uuid, x, y, link[1], link[2])

        log.info('Loading network routes from output plans file.')
        self.routes = self.fetch_routes(planspath)

        log.info('Building spatial index on centroids.')
        idx = index.Index(centroid.entry() for centroid in self.centroids.values())

        log.info('Connecting links to nearest centroid.')
        count = 0
        n = 1
        for link in self.links.values():
            uuid = next(idx.nearest(link.entry(), 1))
            link.centroid = self.centroids[uuid]
            count += 1
            if count == n:
                log.info(f'Connected link {count}.')
                n <<= 1
        if count != n >> 1:
            log.info(f'Connected link {count}.')


    def get_temperature(self, link, time):
        self.links[link].get_temperature(time)

        
    def get_exposure(self, link, start, stop):
        self.links[link].get_exposure(start, stop)
