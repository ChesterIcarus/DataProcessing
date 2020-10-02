
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
    __slots__ = ('database', 'air_temperatures', 'mrt_temperatures',
        'centroids', 'nodes', 'links', 'parcels')

    def __init__(self, database: SqliteUtil):
        self.database = database
        self.air_temperatures: Dict[str, Temperature] = {}
        self.mrt_temperatures: Dict[str, Temperature] = {}
        self.links: Dict[str, Link] = {}
        self.nodes: Dict[str, Node] = {}
        self.parcels: Dict[str, Parcel] = {}


    def load_temperatures(self, source: str = 'mrt'):
        log.info('Loading network air temperature data.')
        query = '''
            SELECT
                temperature_id,
                temperature_idx,
                temperature
            FROM air_temperatures;
        '''
        self.database.cursor.execute(query)
        rows = self.database.fetch_rows()
        rows = counter(rows, 'Loading air temperature %s.', level=log.DEBUG)

        temps = defaultdict(lambda: [None]*96)
        for temperature_id, temperature_idx, temperature in rows:
            temps[temperature_id][temperature_idx] = temperature
        for uuid, values in temps.items():
            self.air_temperatures[uuid] = Temperature(uuid, values)

        log.info('Loading network mrt temperature data.')
        query = f'''
            SELECT
                temperature_id,
                temperature_idx,
                {source}
            FROM mrt_temperatures;
        '''
        self.database.cursor.execute(query)
        rows = self.database.fetch_rows()
        rows = counter(rows, 'Loading mrt temperature %s.', level=log.DEBUG)


        temps = defaultdict(lambda: [None]*96)
        for temperature_id, temperature_idx, temperature in rows:
            temps[temperature_id][temperature_idx] = temperature
        for uuid, values in temps.items():
            self.mrt_temperatures[uuid] = Temperature(uuid, values)


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
                air_temperature,
                mrt_temperature
            FROM links; 
        '''
        self.database.cursor.execute(query)
        result = self.database.fetch_rows()

        links = counter(result, 'Loading link %s.', level=log.DEBUG)
        for link_id, length, speed, modes, air_temp, mrt_temp in links:
            modes_set = set(NetworkMode(mode) for mode in modes.split(','))
            air_temperature = self.air_temperatures[air_temp]
            mrt_temperature = None
            if mrt_temp is not None:
                mrt_temperature = self.mrt_temperatures[mrt_temp]
                if not mrt_temperature.merged:
                    mrt_temperature.merge_null(air_temperature)
            link = Link(
                link_id,
                length, 
                speed, 
                modes_set,
                air_temperature,
                mrt_temperature
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
        rows = counter(rows, 'Loading parcel %s.', level=log.DEBUG)

        for apn, temperature in rows:
            temp = self.air_temperatures[temperature] 
            parcel = Parcel(apn, temp)
            self.parcels[apn] = parcel
        
    
    def load_network(self, source: str):
        self.load_temperatures(source)
        # self.load_nodes()
        self.load_links()
        self.load_parcels()


    def get_temperature(self, link_id: str, time: int) -> float:
        return self.links[link_id].get_temperature(time)

        
    def get_exposure(self, link_id: str, start: int, stop: int) -> float:
        return self.links[link_id].get_exposure(start, stop)
