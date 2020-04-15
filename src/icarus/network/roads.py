
import subprocess
import logging as log

from xml.etree.ElementTree import iterparse
from shapely.geometry import Point
from shapely.wkt import dumps

from icarus.util.file import multiopen


class Roads:
    def __init__(self, database):
        self.database = database


    def configure(self, region):
        with open('config/trim.poly', 'w') as f:
            f.writelines(('network\n', 'first_area\n'))
            f.writelines((f'{pt[0]}\t{pt[1]}\n' for pt in region))
            f.writelines(('END\n', 'END\n'))


    def map(self, pt2matsim):
        subprocess.run((
            'java', '-Xms8G', '-Xmx8G', 
            '-cp', pt2matsim, 'org.matsim.pt2matsim.run.PublicTransitMapper',
            'config/map.xml'), check=True)


    def transit(self, pt2matsim):
        subprocess.run((
            'java', '-Xms8G', '-Xmx8G', 
            '-cp', pt2matsim, 'org.matsim.pt2matsim.run.Osm2MultimodalNetwork',
            'config/transit.xml'), check=True)


    def schedule(self, pt2matsim, epsg, schedule):
        subprocess.run((
            'java', '-Xms8G', '-Xmx8G', 
            '-cp', pt2matsim, 'org.matsim.pt2matsim.run.Gtfs2TransitSchedule',
            schedule, 'dayWithMostServices', f'EPSG:{epsg}', 
            'tmp/schedule.xml', 'input/transitVehicles.xml'), 
            check=True)
    

    def trim(self, osmosis, osm):
        subprocess.run((
            osmosis, 
            '--read-pbf-fast', 'workers=4', f'file={osm}', 
            '--bounding-polygon', f'file=config/trim.poly', 
            '--tag-filter', 'accept-ways', 'highway=*', 'railway=*', 
            '--tag-filter', 'reject-relations',
            '--used-node', 
            '--write-xml', 'tmp/network.osm'), check=True)


    def parse(self, osm, schedule, region, epsg, pt2matsim, osmosis):
        self.configure(region)
        self.trim(osmosis, osm)
        self.schedule(pt2matsim, epsg, schedule)
        self.transit(pt2matsim)
        self.map(pt2matsim)

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
        self.database.cursor.executemany('INSERT INTO nodes VALUES '
            '(?, ?)', nodes)
        self.database.cursor.executemany('INSERT INTO links VALUES '
            '(?, ?, ?, ?, ?, ?, ?, ?, ?)', links)
        self.database.connection.commit()
        

