
import subprocess
import logging as log

from xml.etree.ElementTree import iterparse
from shapely.strtree import STRtree
from shapely.geometry import Point, Polygon
from shapely.wkt import dumps, loads
from rtree import index

from icarus.util.general import counter
from icarus.util.file import multiopen
from icarus.util.sqlite import SqliteUtil


class Region:
    __slots__ = ('maz', 'region')

    def __init__(self, maz: str, region: Polygon):
        self.maz = maz
        self.region = region
    
    def bounds(self):
        return self.region.bounds


class Centroid:
    __slots__ = ('id', 'x', 'y')

    def __init__(self, uuid, x, y):
        self.id = uuid
        self.x = x
        self.y = y

    def entry(self):
        return (self.id, (self.x, self.y, self.x, self.y), None)



class Roads:
    def __init__(self, database: SqliteUtil):
        self.database = database


    def fetch_regions(self):
        query = '''
            SELECT
                maz,
                region
            FROM regions;   '''
        return self.database.connection.execute(query)

    
    def fetch_centroids(self):
        self.database.cursor.execute('''
            SELECT
                centroid_id,
                center
            FROM centroids; ''')
        return self.database.cursor.fetchall()


    def create_tables(self):
        self.database.drop_table('nodes')
        self.database.drop_table('links')
        self.database.cursor.execute('''
            CREATE TABLE nodes(
                node_id VARCHAR(255),
                maz SMALLINT UNSIGNED,
                centroid_id MEDIUMINT UNSIGNED,
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
        self.database.connection.commit()

    
    def ready(self, networkpath):
        tables = ('regions', 'centroids')
        exists = self.database.table_exists(*tables)
        if len(exists) < len(tables):
            missing = ', '.join(set(tables) - set(exists))
            log.info(f'Could not find tables {missing} in database.')
        return len(exists) == len(tables)


    def complete(self):
        tables = ('nodes', 'links')
        exists = self.database.table_exists(*tables)
        if len(exists):
            present = ', '.join(exists)
            log.info(f'Found tables {present} already in database.')
        return len(exists) > 0


    def parse(self, networkpath):
        log.info('Fetching exposure geospatial data.')
        centroids_list = self.fetch_centroids()

        log.info('Loading centroids into spatial index.')
        centroids = {}
        for uuid, centroid in counter(centroids_list, 'Loading centroid %s.'):
            x, y = map(float, centroid[7:-1].split(' '))
            centroids[uuid] = Centroid(uuid, x, y)

        centroid_idx = index.Index(centroid.entry() 
            for centroid in centroids.values())
        del centroids_list

        log.info('Fetching network region data.')
        regions_list = self.fetch_regions()

        log.info('Loading regions into spatial index.')
        regions = {}
        for uuid, region in counter(regions_list, 'Loading region %s.'):
            polygon = loads(region)
            setattr(polygon, 'maz', uuid)
            regions[uuid] = Region(uuid, polygon)

        region_idx = STRtree(region.region for region in regions.values())
        del regions_list


        def get_centroid(node):
            return next(centroid_idx.nearest(node, 1))
        
        def get_region(node: Point):
            regions = region_idx.query(node)
            region = None
            if len(regions):
                region = regions[0].maz
            return region


        log.info('Loading network roads file.')
        network = multiopen(networkpath, mode='rb')
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
                    point = Point(x, y)
                    region = get_region(point)
                    centroid = get_centroid((x, y, x, y))
                    nodes.append((
                        str(elem.get('id')),
                        region,
                        centroid,
                        dumps(point)))
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
        self.database.insert_values('nodes', nodes, 4)
        self.database.insert_values('links', links, 9)
        self.database.connection.commit()
        

