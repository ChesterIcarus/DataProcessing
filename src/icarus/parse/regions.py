
import os
import shapefile
import logging as log

from argparse import ArgumentParser, SUPPRESS
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


def parse_regions(database: SqliteUtil, regions_file: str, prj_crs: str):
    log.info('Allocating tables for regions.')
    create_tables(database)

    prjpath = os.path.splitext(regions_file)[0] + '.prj'
    with open(prjpath, 'r') as prjfile:
        src_crs = prjfile.read()

    log.info('Loading network nodes.')
    nodes = load_nodes(database)

    def load():
        for idx, node in nodes.items():
            pt = node.point
            yield (idx, (pt.x, pt.y, pt.x, pt.y), None)

    log.info('Building spatial index from nodes.')
    index = Index(load())

    transformer = Transformer.from_crs(src_crs, prj_crs,
        always_xy=True, skip_equivalent=True)
    project = transformer.transform

    log.info('Parsing regions from shapefile.')
    parser = shapefile.Reader(regions_file)
    iter_regions = counter(iter(parser), 'Parsing region %s.', level=log.DEBUG)

    regions = []
    for item in iter_regions:
        maz = item.record.ID
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
            item.record.TAZ_2019,
            item.record.AREA,
            dumps(polygon.centroid),
            dumps(polygon)
        ))

    parser.close()

    null = sum((1 for node in nodes.values() if node.maz is None))
    total = len(nodes)

    if null > 0:
        perc = round(null / total * 100, 2)
        log.warning(f'Found {perc}% ({null}) nodes not assigned an MAZ.')
    
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
    desc = (
        'Parse regions from the city zoing data. '
    )
    parser = ArgumentParser('icarus.parse.regions', description=desc, 
        add_help=False)

    general = parser.add_argument_group('general options')
    general.add_argument('--help', action='help', default=SUPPRESS,
        help='show this help menu and exit process')
    general.add_argument('--dir', type=str, dest='dir', default='.',
        help='path to simulation data; default is current working directory')
    general.add_argument('--log', type=str, dest='log', default=None,
        help='location to save additional logfiles')
    general.add_argument('--level', type=str, dest='level', default='info',
        choices=('notset', 'debug', 'info', 'warning', 'error', 'critical'),
        help='level of verbosity to print log messages')
    general.add_argument('--force', action='store_true', dest='force', 
        default=False, help='skip prompts for deleting files/tables')

    args = parser.parse_args()

    path = lambda x: os.path.abspath(os.path.join(args.dir, x))
    os.makedirs(path('logs'), exist_ok=True)
    homepath = path('')
    logpath = path('logs/parse_regions.log')
    dbpath = path('database.db')
    configpath = path('config.json')

    handlers = []
    handlers.append(log.StreamHandler())
    handlers.append(log.FileHandler(logpath))
    if args.log is not None:
        handlers.append(log.FileHandler(args.log, 'w'))
    log.basicConfig(
        format='%(asctime)s %(levelname)s %(filename)s:%(lineno)s %(message)s',
        level=getattr(log, args.level.upper()),
        handlers=handlers
    )

    log.info('Running regions parsing module.')
    log.info(f'Loading data from {homepath}.')
    log.info('Verifying process metadata/conditions.')

    config = ConfigUtil.load_config(configpath)
    database = SqliteUtil(dbpath)

    regions_file = config['network']['regions']['region_file']

    if not ready(database, regions_file):
        log.error('Process dependencies not met; see warnings and '
            'documentation for more details.')
        exit(1)
    if complete(database) and not args.force:
        log.error('Some or all of this process is already complete.')
        log.error('Would you like to continue? [Y/n]')
        if input().lower() not in ('y', 'yes', 'yeet'):
            exit()

    try:
        log.info('Starting regions parsing.')
        parse_regions(database, regions_file, 'epsg:2223')
    except:
        log.exception('Critical error while parsing regions; '
            'terminating process and exiting.')
        exit(1)


if __name__ == '__main__':
    main()
