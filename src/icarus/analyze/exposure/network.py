
from __future__ import annotations

import os
import logging as log
from typing import List, Set, Dict

from icarus.analyze.exposure.centroid import Centroid
from icarus.analyze.exposure.node import Node
from icarus.analyze.exposure.link import Link
from icarus.analyze.exposure.types import NetworkMode
from icarus.util.sqlite import SqliteUtil
from icarus.util.general import counter, defaultdict


def xy(point: str) -> tuple:
    return tuple(map(float, point[7:-1].split(' ')))


class Network:
    __slots__ = ('database', 'temperatures', 'centroids', 'nodes', 'links')

    def __init__(self, database: SqliteUtil):
        self.database = database
        self.temperatures = defaultdict(lambda x: [])
        self.centroids: Dict[str, Centroid] = {}
        self.links: Dict[str, Link] = {}
        self.nodes: Dict[str, Node] = {}


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
        for temperature_id, _, temperature in temperatures:
            self.temperatures[temperature_id].append(temperature)
        self.temperatures.lock()


    def load_centroids(self):
        log.info('Loading network daymet centroid data.')
        centroids = counter(self.fetch_centroids(), 'Loading centroid %s.')
        for centroid_id, temperature_id, center in centroids:
            temperatures = self.temperatures[temperature_id]
            x, y = xy(center)
            self.centroids[centroid_id] = Centroid(centroid_id, temperatures, x, y)


    def load_nodes(self):
        log.info('Loading network road node data.')
        nodes = counter(self.fetch_nodes(), 'Loading node %s.')
        for node_id, maz, centroid_id, point in nodes:
            centroid = self.centroids[centroid_id]
            x, y = xy(point)
            self.nodes[node_id] = Node(node_id, maz, centroid, x, y)


    def load_links(self):
        log.info('Loading network road link data.')
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

    
    def load_network(self):
        self.load_temperatures()
        self.load_centroids()
        self.load_nodes()
        self.load_links()


    def get_temperature(self, link_id: str, time: int) -> float:
        return self.links[link_id].get_temperature(time)

        
    def get_exposure(self, link_id: str, start: int, stop: int) -> float:
        return self.links[link_id].get_exposure(start, stop)
