
from __future__ import annotations

import os
import logging as log
from typing import List, Set, Dict

from icarus.analyze.exposure.centroid import Centroid
from icarus.analyze.exposure.node import Node
from icarus.analyze.exposure.link import Link
from icarus.analyze.exposure.parcel import Parcel
from icarus.analyze.exposure.types import NetworkMode
from icarus.analyze.exposure.temperature import Temperature
from icarus.util.sqlite import SqliteUtil
from icarus.util.general import counter, defaultdict


def xy(point: str) -> tuple:
    return tuple(map(float, point[7:-1].split(' ')))


class Network:
    __slots__ = ('database', 'temperatures', 'centroids', 
        'nodes', 'links', 'parcels')

    def __init__(self, database: SqliteUtil):
        self.database = database
        self.temperatures: Dict[str, Temperature] = {}
        self.links: Dict[str, Link] = {}
        self.nodes: Dict[str, Node] = {}
        self.parcels: Dict[str, Parcel] = {}


    def load_temperatures(self):
        log.info('Loading network temperature data.')
        query = '''
            SELECT
                temperature_id,
                temperature_idx,
                temperature
            FROM air_temperatures
            ORDER BY
                temperature_id,
                temperature_idx;
        '''
        self.database.cursor.execute(query)
        result = self.database.cursor.fetchall()

        temps = defaultdict(lambda: [])
        temperatures = counter(result, 'Loading temperature %s.')
        for temperature_id, _, temperature in temperatures:
            temps[temperature_id].append(temperature)
        for uuid, values in temps.items():
            self.temperatures[uuid] = Temperature(uuid, values)


    # def load_nodes(self):
    #     query = f'''
    #         SELECT
    #             node_id,
    #             maz,
    #             point
    #         FROM nodes;
    #     '''
    #     self.database.cursor.execute(query)
    #     result = self.database.cursor.fetchall()

    #     nodes = counter(result, 'Loading node %s.')
    #     for node_id, maz, point in nodes:
    #         x, y = xy(point)
    #         self.nodes[node_id] = Node(node_id, maz, x, y)


    def load_links(self):
        log.info('Loading network road link data.')
        query = '''
            SELECT
                link_id,
                length,
                freespeed,
                modes,
                air_temperature
            FROM links; 
        '''
        self.database.cursor.execute(query)
        result = self.database.cursor.fetchall()

        links = counter(result, 'Loading link %s.')
        for link_id, length, speed, modes, temp in links:
            modes_set = set(NetworkMode(mode) for mode in modes.split(','))
            temperature = self.temperatures[temp]
            link = Link(
                link_id,
                length, 
                speed, 
                modes_set,
                temperature
            )
            self.links[link_id] = link

    
    def load_parcels(self):
        log.info('Loading network parcel data.')
        query = '''
            SELECT
                apn,
                air_temperature
            FROM parcels;
        '''
        self.database.cursor.execute(query)
        rows = self.database.fetch_rows()
        rows = counter(rows, 'Loading parcel %s.')

        for apn, temperature in rows:
            temp = self.temperatures[temperature] 
            parcel = Parcel(apn, temp)
            self.parcels[apn] = parcel
        
    
    def load_network(self, source: str):
        self.load_temperatures()
        # self.load_nodes()
        self.load_links()
        self.load_parcels()


    def get_temperature(self, link_id: str, time: int) -> float:
        return self.links[link_id].get_temperature(time)

        
    def get_exposure(self, link_id: str, start: int, stop: int) -> float:
        return self.links[link_id].get_exposure(start, stop)
