
from __future__ import annotations

import os
import psutil
import logging as log
from typing import List, Set

from icarus.parse.events.types import NetworkMode
from icarus.util.sqlite import SqliteUtil
from icarus.util.general import counter, defaultdict


def xy(point: str) -> tuple:
    return tuple(map(float, point[7:-1].split(' ')))


def mem():
    process = psutil.Process(os.getpid())
    mem = process.memory_info().rss
    return round(mem / (10 ** 6))



class Centroid:
    __slots__ = ('id', 'temperatures', 'x', 'y')
        
    def __init__(self, centroid_id: int, temperatures: List[float], 
            x: int, y: int):
        self.id = centroid_id
        self.temperatures = temperatures
        self.x = x
        self.y = y


    def get_temperature(self, time: int) -> float:
        steps = len(self.temperatures)
        step = int(time / 86400 * steps) % steps
        return self.temperatures[step]


    def get_exposure(self, start: int, stop: int) -> float:
        steps = len(self.temperatures)
        step_size = int(86400 / steps)
        start_step = int(start / 86400 * steps)
        stop_step = int(stop / 86400 * steps)
        exposure = 0
        if start_step == stop_step:
            exposure = (stop - start) * self.temperatures[start_step % steps]
        else:
            exposure = ((start_step + 1) * step_size - start) * \
                self.temperatures[start_step % steps]
            for step in range(start_step + 1, stop_step):
                exposure += step_size * self.temperatures[step % steps]
            exposure += (stop - stop_step * step_size) * \
                self.temperatures[stop_step % steps]
        return exposure



class Node:
    __slots__= ('id', 'maz', 'centroid', 'x', 'y')

    def __init__(self, node_id: str, maz: int, centroid: Centroid, 
            x: float, y:float):
        self.id = node_id
        self.maz = maz
        self.centroid = centroid
        self.x = x
        self.y = y

    def get_temperature(self, time: int) -> float:
        return self.centroid.get_temperature(time)


    def get_exposure(self, start: int, stop: int) -> float:
        return self.centroid.get_exposure(start, stop)



class Link:
    __slots__ = ('length', 'freespeed', 'src_node', 'term_node', 'id', 
            'capacity', 'modes')

    def __init__(self, link_id: str, src_node: Node, term_node: Node, 
            length: float, freespeed: float, modes: Set[NetworkMode]):
        self.id = link_id
        self.src_node = src_node
        self.term_node = term_node
        self.length = length
        self.freespeed = freespeed
        self.modes = modes

    
    def get_temperature(self, time: int) -> float:
        return self.src_node.get_temperature(time)


    def get_exposure(self, start: int, stop: int) -> float:
        return self.src_node.get_exposure(start, stop)



class Network:
    __slots__ = ('database', 'temperatures', 'centroids', 'nodes', 'links')

    def __init__(self, database: SqliteUtil):
        self.database = database
        self.temperatures = defaultdict(lambda x: [])
        self.centroids = {}
        self.links = {}
        self.nodes = {}


    def fetch_temperatures(self) -> List[List]:
        self.database.cursor.execute('''
            SELECT
                temperature_id,
                temperature_idx,
                temperature
            FROM temperatures
            ORDER BY
                temperature_id,
                temperature_idx;    ''')
        return self.database.cursor.fetchall()

    
    def fetch_centroids(self) -> List[List]:
        self.database.cursor.execute('''
            SELECT
                centroid_id,
                temperature_id,
                center
            FROM centroids; ''')
        return self.database.cursor.fetchall()

    
    def fetch_nodes(self) -> List[List]:
        self.database.cursor.execute('''
            SELECT
                node_id,
                maz,
                centroid_id,
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


    def load_temperatures(self):
        log.info('Loading network daymet temperature data.')
        temperatures = counter(self.fetch_temperatures(), 'Loading temperature %s.')
        for temperature in temperatures:
            temperature_id = temperature[0]
            value = temperature[1]
            self.temperatures[temperature_id].append(value)
        self.temperatures.lock()


    def load_centroids(self):
        log.info('Loading network daymet centroid data.')
        centroids = counter(self.fetch_centroids(), 'Loading centroid %s.')
        for centroid in centroids:
            centroid_id = centroid[0]
            temperatures = self.temperatures[centroid[1]]
            x, y = xy(centroid[2])
            self.centroids[centroid_id] = Centroid(centroid_id, temperatures, x, y)


    def load_nodes(self):
        log.info('Loading network road node data.')
        nodes = counter(self.fetch_nodes(), 'Loading nodes %s.')
        for node in nodes:
            node_id = node[0]
            maz = node[1]
            centroid = self.centroids[node[2]]
            x, y = xy(node[3])
            self.nodes[node_id] = Node(node_id, maz, centroid, x, y)


    def load_links(self):
        log.info('Fetching network road link data.')
        links = counter(self.fetch_links(), 'Loading link %s.')
        for link in links:
            try:
                link_id = link[0]
                src_node = self.nodes[link[1]]
                term_node = self.nodes[link[2]]
                length = link[3]
                freespeed = link[4]
                modes = set(NetworkMode(mode) for mode in link[5].split(','))
                self.links[link_id] = Link(link_id, src_node, term_node, 
                    length, freespeed, modes)
            except:
                breakpoint()

    
    def load_network(self):
        log.info('Loading network data.')

        log.info(f'Memory usage before loading netowrk: {mem()} MB.')
        self.load_temperatures()
        self.load_centroids()
        self.load_nodes()
        self.load_links()

        log.info('Network loading complete.')
        log.info(f'Memory usage after loading network: {mem()} MB.')


    def get_temperature(self, link_id: str, time: int) -> float:
        return self.links[link_id].get_temperature(time)

        
    def get_exposure(self, link_id: str, start: int, stop: int) -> float:
        return self.links[link_id].get_exposure(start, stop)
