
import logging as log

from xml.etree.ElementTree import iterparse
from shapely.strtree import STRtree
from shapely.geometry import Point, Polygon, LineString
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

    
    def fetch_daymet_centroids(self):
        self.database.cursor.execute('''
            SELECT
                centroid_id,
                point
            FROM daymet_centroids; ''')
        return self.database.cursor.fetchall()

    
    def fetch_mrt_centroids(self):
        self.database.cursor.execute('''
            SELECT
                centroid_id,
                point
            FROM mrt_centroids; ''')
        return self.database.cursor.fetchall()


    def create_tables(self):
        self.database.drop_table('nodes')
        self.database.drop_table('links')
        self.database.cursor.execute('''
            CREATE TABLE nodes(
                node_id VARCHAR(255),
                maz SMALLINT UNSIGNED,
                daymet_centroid MEDIUMINT UNSIGNED,
                mrt_centroid INT UNSIGNED,
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
                modes VARHCAR(255),
                line VARHCAR(255)
            );  ''')
        self.database.connection.commit()

    
    def create_indexes(self):
        query = f'''
            CREATE INDEX nodes_node
            ON nodes(node_id); '''
        self.database.cursor.execute(query)
        query = f'''
            CREATE INDEX links_link
            ON links(link_id); '''
        self.database.cursor.execute(query)
        query = f'''
            CREATE INDEX links_node1
            ON links(source_node); '''
        self.database.cursor.execute(query)
        query = f'''
            CREATE INDEX links_node2
            ON links(terminal_node); '''
        self.database.cursor.execute(query)
        self.database.connection.commit()

    
    def ready(self, networkpath):
        tables = ('regions', 'daymet_centroids', 'mrt_centroids')
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
        daymet_list = self.fetch_daymet_centroids()
        daymet_list = counter(daymet_list, 'Loading daymet centroid %s.')
        mrt_list = self.fetch_mrt_centroids()
        mrt_list = counter(mrt_list, 'Loading mrt centroid %s.')

        log.info('Loading centroids into spatial index.')
        daymet_centroids = {}
        mrt_centroids = {}
        for centroid_id, point in daymet_list:
            x, y = map(float, point[7:-1].split(' '))
            centroid = Centroid(centroid_id, x, y)
            daymet_centroids[centroid_id] = centroid
        daymet_centroid_idx = index.Index(centroid.entry() 
            for centroid in daymet_centroids.values())
        for centroid_id, point in mrt_list:
            x, y = map(float, point[7:-1].split(' '))
            centroid = Centroid(centroid_id, x, y)
            mrt_centroids[centroid_id] = centroid
        mrt_centroid_idx = index.Index(centroid.entry() 
            for centroid in mrt_centroids.values())

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


        def get_daymet_centroid(node):
            return next(daymet_centroid_idx.nearest(node, 1))

        def get_mrt_centroid(node):
            return next(mrt_centroid_idx.nearest(node, 1))
        
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
        points = {}
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
                        log.info(f'Parsing node {count}.')
                    log.info('Parsing links from network file.')
                    count = 0
                    n = 1
            elif evt == 'end':
                if elem.tag == 'node':
                    node_id = str(elem.get('id'))
                    x = float(elem.get('x'))
                    y = float(elem.get('y'))
                    point = Point(x, y)
                    region = get_region(point)
                    daymet_centroid = get_daymet_centroid((x, y, x, y))
                    mrt_centroid = get_mrt_centroid((x, y, x, y))
                    nodes.append((
                        node_id,
                        region,
                        daymet_centroid,
                        mrt_centroid,
                        dumps(point)
                    ))
                    points[node_id] = point
                    count += 1
                    if count == n:
                        log.info(f'Parsing node {count}.')
                        n <<= 1
                elif elem.tag == 'link':
                    source_node = str(elem.get('from'))
                    terminal_node = str(elem.get('to'))
                    line = LineString((
                        points[source_node], 
                        points[terminal_node]
                    ))
                    links.append((
                        str(elem.get('id')),
                        source_node,
                        terminal_node,
                        float(elem.get('length')),
                        float(elem.get('freespeed')),
                        float(elem.get('capacity')),
                        float(elem.get('permlanes')),
                        int(elem.get('oneway')),
                        str(elem.get('modes')),
                        dumps(line) 
                    ))
                    count += 1
                    if count == n:
                        log.info(f'Parsing link {count}.')
                        n <<= 1
                    if count % 100000:
                        root.clear()

        if count != n << 1:
            log.info(f'Parsing link {count}.')
        network.close() 

        log.info('Writing parsed links and nodes to database.')
        self.create_tables()
        self.database.insert_values('nodes', nodes, 5)
        self.database.insert_values('links', links, 10)
        self.database.connection.commit()
        
