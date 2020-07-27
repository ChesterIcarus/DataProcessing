
import os
import shapefile
import logging as log

from argparse import ArgumentParser
from rtree.index import Index
from pyproj import Transformer
from shapely.geometry import Polygon, Point
from shapely.wkt import dumps, loads

from icarus.util.config import ConfigUtil
from icarus.util.general import counter
from icarus.util.sqlite import SqliteUtil


class Node:
    __slots__ = ('uuid', 'point', 'maz')

    def __init__(self, uuid: str, point: Point, maz: int):
        self.uuid = uuid
        self.point = point
        self.maz = maz


def xy(point: str) -> tuple:
    return tuple(map(float, point[7:-1].split(' ')))


def complete(database: SqliteUtil):
    done = False
    exists = database.table_exists('regions')
    if len(exists):
        log.warning('Database already has table regions.')
        done = True

    return done


def ready(database: SqliteUtil, regions_file: str):
    ready = True

    exists = os.path.exists(regions_file)
    if not exists:
        log.warning(f'Could not open file {regions_file}.')
        ready = False

    tables = ('nodes',)
    exists = database.table_exists(*tables)
    missing = set(tables) - set(exists)
    for table in missing:
        log.warning(f'Could not find table {table}.')
        ready = False

    return ready


def create_tables(database: SqliteUtil):
    database.drop_table('regions')
    database.drop_index('nodes_region')
    query = '''
        CREATE TABLE regions(
            maz SMALLINT UNSIGNED,
            taz SMALLINT UNSIGNED,
            area FLOAT,
            center VARCHAR(255),
            region TEXT
        );  
    '''
    database.cursor.execute(query)
    database.connection.commit()


def create_indexes(database: SqliteUtil):
    query = '''
        CREATE INDEX regions_maz
        ON regions(maz); 
    '''
    database.cursor.execute(query)
    query = '''
        CREATE INDEX nodes_region
        ON nodes(maz);
    '''
    database.cursor.execute(query)
    database.connection.commit()


def load_nodes(database: SqliteUtil):
    nodes = {}
    query = '''
        SELECT
            node_id,
            point
        FROm nodes;
    '''
    database.cursor.execute(query)
    result = database.fetch_rows()
    
    for idx, (uuid, point) in enumerate(result):
        pt = Point(loads(point))
        nodes[idx] = Node(uuid, pt, None)
    
    return nodes


def parse_regions(database: SqliteUtil, regions_file: str, src_epsg: int, 
        prj_epsg: int):

    log.info('Allocating tables for regions.')
    create_tables(database)

    transformer = Transformer.from_crs(f'epsg:{src_epsg}', 
        f'epsg:{prj_epsg}', always_xy=True, skip_equivalent=True)
    project = transformer.transform

    log.info('Loading network nodes.')
    nodes = load_nodes(database)

    log.info('Building spatial index from nodes.')

    def load():
        for idx, node in nodes.items():
            pt = node.point
            yield (idx, (pt.x, pt.y, pt.x, pt.y), None)

    index = Index(load())

    log.info('Parsing regions from shapefile.')
    parser = shapefile.Reader(regions_file)
    iter_regions = counter(iter(parser), 'Parsing region %s.')
    regions = []
    for item in iter_regions:
        maz = item.record.MAZ_ID_10
        points = (project(*point) for point in item.shape.points)
        polygon = Polygon(points)
        result = index.intersection(polygon.bounds)

        for idx in result:
            node = nodes[idx]
            if polygon.contains(node.point):
                if node.maz is not None:
                    warning = 'Node %s is in both region %s and %s; ' \
                        'the latter region will be kept.'
                    log.warning(warning % (node.uuid, node.maz, maz))
                node.maz = maz
        
        regions.append((
            maz,
            item.record.TAZ_2015,
            item.record.Sq_miles,
            dumps(polygon.centroid),
            dumps(polygon)
        ))

    parser.close()
    
    log.info('Writing parsed regions to database.')
    database.insert_values('regions', regions, 5)
    database.connection.commit()

    log.info('Updating node region data.')
    
    def dump_nodes():
        for node in nodes.values():
            yield (node.maz, node.uuid)

    query = '''
        UPDATE nodes
        SET maz = :maz
        WHERE node_id = :node_id; 
    '''
    database.cursor.executemany(query, dump_nodes())
    database.connection.commit()

    log.info('Creating indexes on new tables.')
    create_indexes(database)


def main():
    parser = ArgumentParser('daymet air temperature parser')
    
    parser.add_argument('--dir', type=str, dest='dir', default='.',
        help='path to directory containing Icarus run data')
    parser.add_argument('--log', type=str, dest='log', default=None,
        help='path to file to save the process log; not saved by default')
    parser.add_argument('--level', type=str, dest='level', default='info',
        choices=('notset', 'debug', 'info', 'warning', 'error', 'critical'),
        help='verbosity of the process log')

    args = parser.parse_args()

    handlers = []
    handlers.append(log.StreamHandler())
    if args.log is not None:
        handlers.append(log.FileHandler(args.log, 'w'))
    log.basicConfig(
        format='%(asctime)s %(levelname)s %(filename)s:%(lineno)s %(message)s',
        level=getattr(log, args.level.upper()),
        handlers=handlers
    )

    path = lambda x: os.path.abspath(os.path.join(args.dir, x))
    home = path('')

    config = ConfigUtil.load_config(path('config.json'))
    database = SqliteUtil(path('database.db'))

    regions_file = config['network']['regions']['region_file']

    log.info('Running regions parsing tool.')
    log.info(f'Loading run data from {home}.')

    if not ready(database, regions_file):
        log.error('Process dependencies not met; see warnings and '
            'documentation for more details.')
        exit(1)
    if complete(database):
        log.info('All or some of this process is already complete. '
            ' Would you like to proceed? [Y/n]')
        valid = ('y', 'n', 'yes', 'no', 'yee', 'naw')
        response = input().lower()
        while response not in valid:
            print('Try again; would you like to proceed? [Y/n]')
            response = input().lower()
        if response in ('n', 'no', 'naw'):
            log.info('User chose to terminate process.')
            exit()

    try:
        log.info('Starting regions parsing.')
        parse_regions(database, regions_file, 2223, 2223)
    except:
        log.exception('Critical error while parsing regions; '
            'terminating process and exiting.')
        exit(1)


if __name__ == '__main__':
    main()
