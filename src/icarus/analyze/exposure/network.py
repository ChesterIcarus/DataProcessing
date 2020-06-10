
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


    def load_temperatures(self, source: str):
        log.info('Loading network temperature data.')
        if source == 'air':
            query = '''
                SELECT
                    temperature_id,
                    temperature_idx,
                    temperature
                FROM daymet_temperatures
                ORDER BY
                    temperature_id,
                    temperature_idx;
            '''
        elif source in ('mrt', 'pet', 'utci'):
            query = f'''
                SELECT DISTINCT
                    centroid_id,
                    time,
                    {source}
                FROM mrt_temperatures
                INNER JOIN nodes
                ON nodes.mrt_centroid = mrt_temperatures.centroid_id
                ORDER BY
                    centroid_id,
                    time;
            '''
        self.database.cursor.execute(query)
        result = self.database.cursor.fetchall()

        temperatures = counter(result, 'Loading temperature %s.')
        for temperature_id, _, temperature in temperatures:
            self.temperatures[temperature_id].append(temperature)
        self.temperatures.lock()


    def load_centroids(self, source: str):
        log.info('Loading network centroid data.')
        if source == 'air':
            query = '''
                SELECT
                    centroid_id,
                    temperature_id,
                    point
                FROM daymet_centroids
                INNER JOIN nodes
                ON daymet_centroids.centroid_id == nodes.daymet_centroid;
            '''
        elif source in ('mrt', 'pet', 'utci'):
            query = '''
                SELECT
                    centroid_id,
                    centroid_id,
                    point
                FROM mrt_centorids
                INNER JOIN nodes
                ON daymet_centroids.centroid_id == nodes.mrt_centroid;
            '''

        self.database.cursor.execute(query)
        result = self.database.cursor.fetchall()

        centroids = counter(result, 'Loading centroid %s.')
        for centroid_id, temperature_id, center in centroids:
            temperatures = self.temperatures[temperature_id]
            x, y = xy(center)
            centroid = Centroid(centroid_id, temperatures, x, y)
            self.centroids[centroid_id] = centroid


    def load_nodes(self, source: str):
        log.info('Loading network road node data.')
        if source == 'air':
            field = 'daymet_cetroid'
        elif source in ('mrt', 'pet', 'utci'):
            field = 'mrt_centroid' 
        query = f'''
            SELECT
                node_id,
                maz,
                {field},
                point
            FROM nodes;
        '''
        self.database.cursor.execute(query)
        result = self.database.cursor.fetchall()

        nodes = counter(result, 'Loading node %s.')
        for node_id, maz, centroid_id, point in nodes:
            centroid = self.centroids[centroid_id]
            x, y = xy(point)
            self.nodes[node_id] = Node(node_id, maz, centroid, x, y)


    def load_links(self):
        log.info('Loading network road link data.')
        query = '''
            SELECT
                link_id,
                source_node,
                terminal_node,
                length,
                freespeed,
                modes
            FROM links; 
        '''
        self.database.cursor.execute(query)
        result = self.database.cursor.fetchall()

        links = counter(result, 'Loading link %s.')
        for link_id, src_node, term_node, length, freespeed, modes in links:
            modes_set = set(NetworkMode(mode) for mode in modes.split(','))
            link = Link(
                link_id, 
                self.nodes[src_node], 
                self.nodes[term_node], 
                length, 
                freespeed, 
                modes_set
            )
            self.links[link_id] = link

    
    def load_network(self, source: str):

        self.load_temperatures(source)
        self.load_centroids(source)
        self.load_nodes(source)
        self.load_links()


    def get_temperature(self, link_id: str, time: int) -> float:
        return self.links[link_id].get_temperature(time)

        
    def get_exposure(self, link_id: str, start: int, stop: int) -> float:
        return self.links[link_id].get_exposure(start, stop)
