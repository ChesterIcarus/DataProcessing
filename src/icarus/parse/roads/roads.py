
import subprocess
import logging as log

from xml.etree.ElementTree import iterparse
from shapely.geometry import Point
from shapely.wkt import dumps

from icarus.util.file import multiopen
from icarus.util.sqlite import SqliteUtil


class Roads:
    def __init__(self, database: SqliteUtil):
        self.database = database

    
    def complete(self):
        tables = ('nodes', 'links')
        return len(self.database.table_exists(*tables)) == len(tables)


    def create_tables(self):
        self.database.drop_table('nodes')
        self.database.drop_table('links')
        self.database.cursor.execute('''
            CREATE TABLE nodes(
                node_id VARCHAR(255),
                point VARCHAR(255)
            );  ''')
        self.database.cursor.execute('''
            CREATE TABLE links(
                link_id VARCHAR(255),
                source_node VARCHAR(255),
                terminal_node VARCHAR(255),
                length FLOAT,
                freespeed FLOAT,
                capacity FLOAT,
                permlanes FLOAT,
                oneway TINYINT UNSIGNED,
                modes VARHCAR(255)
            );  ''')


    def parse(self):
        network = multiopen('input/network.xml', mode='rb')
        parser = iter(iterparse(network, events=('start', 'end')))
        evt, root = next(parser)

        links = []
        nodes = []
        count = 0
        n = 1

        for evt, elem in parser:
            if evt == 'start':
                if elem.tag == 'nodes':
                    log.info('Parsing nodes from network file.')
                    count = 0
                    n = 1
                elif elem.tag == 'links':
                    if count != n << 1:
                        log.info(f'Parsed node {count}.')
                    log.info('Parsing links from network file.')
                    count = 0
                    n = 1
            elif evt == 'end':
                if elem.tag == 'node':
                    x = float(elem.get('x'))
                    y = float(elem.get('y'))
                    nodes.append((
                        str(elem.get('id')),
                        dumps(Point(x, y))))
                    count += 1
                    if count == n:
                        log.info(f'Parsed node {count}.')
                        n <<= 1
                elif elem.tag == 'link':
                    links.append((
                        str(elem.get('id')),
                        str(elem.get('from')),
                        str(elem.get('to')),
                        float(elem.get('length')),
                        float(elem.get('freespeed')),
                        float(elem.get('capacity')),
                        float(elem.get('permlanes')),
                        int(elem.get('oneway')),
                        str(elem.get('modes'))))
                    count += 1
                    if count == n:
                        log.info(f'Parsed link {count}.')
                        n <<= 1
                    if count % 100000:
                        root.clear()

        if count != n << 1:
            log.info(f'Parsed link {count}.')
        network.close() 

        log.info('Writing parsed links and nodes to database.')
        self.create_tables()
        self.database.insert_values('nodes', nodes, 2)
        self.database.insert_values('links', links, 9)
        self.database.connection.commit()
        

