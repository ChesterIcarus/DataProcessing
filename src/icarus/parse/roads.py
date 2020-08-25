
import os
import logging as log

from argparse import ArgumentParser, SUPPRESS
from xml.etree.ElementTree import iterparse
from pyproj.transformer import Transformer

from icarus.util.file import multiopen
from icarus.util.config import ConfigUtil
from icarus.util.sqlite import SqliteUtil


def ready(networkpath: str):
    ready = True
    present = os.path.exists(networkpath)
    if not present:
        log.warning(f'Could not open file {networkpath}.')
        ready = False

    return ready


def complete(database: SqliteUtil):
    complete = False
    tables = ('nodes', 'links')
    present = database.table_exists(*tables)
    for table in present:
        log.warning(f'Table {table} already exists.')
        complete = True

    return complete


def create_tables(database: SqliteUtil):
    database.drop_table('nodes', 'links')
    query = '''
        CREATE TABLE nodes(
            node_id VARCHAR(255),
            maz SMALLINT UNSIGNED,
            point VARCHAR(255)
        );
    '''
    database.cursor.execute(query)
    query = '''
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
            air_temperature INT UNSIGNED,
            mrt_temperature INT UNSIGNED,
            exposure FLOAT
        );
    '''
    database.cursor.execute(query)
    database.connection.commit()


def create_indexes(database: SqliteUtil):
    query = '''
        CREATE INDEX nodes_node
        ON nodes(node_id);
    '''
    database.cursor.execute(query)
    query = '''
        CREATE INDEX links_link
        ON links(link_id);
    '''
    database.cursor.execute(query)
    query = '''
        CREATE INDEX links_node1
        ON links(source_node);
    '''
    database.cursor.execute(query)
    query = '''
        CREATE INDEX links_node2
        ON links(terminal_node);
    '''
    database.cursor.execute(query)
    database.connection.commit()


def parse_roads(database: SqliteUtil, networkpath: str,
        src_epsg: int, prj_epsg: int):
    log.info('Allocating tables for network links and nodes.')
    create_tables(database)

    log.info('Loading network roads file.')
    network = multiopen(networkpath, mode='rb')
    parser = iter(iterparse(network, events=('start', 'end')))
    evt, root = next(parser)

    transformer = Transformer.from_crs(f'epsg:{src_epsg}', 
        f'epsg:{prj_epsg}', always_xy=True, skip_equivalent=True)
    project = transformer.transform

    links = []
    nodes = []
    count, n = 0, 1

    for evt, elem in parser:
        if evt == 'start':
            if elem.tag == 'nodes':
                log.info('Parsing nodes from network file.')
                count, n = 0, 1
                root.clear()
            elif elem.tag == 'links':
                if count != n << 1:
                    log.debug(f'Parsing node {count}.')
                log.info('Parsing links from network file.')
                count, n = 0, 1
                root.clear()
        elif evt == 'end':
            if elem.tag == 'node':
                node_id = str(elem.get('id'))
                x = float(elem.get('x'))
                y = float(elem.get('y'))
                x, y = project(x, y)
                wkt = f'POINT ({x} {y})'
                nodes.append((
                    node_id,
                    None,
                    wkt
                ))
                count += 1
                if count == n:
                    log.debug(f'Parsing node {count}.')
                    n <<= 1
                if count % 100000 == 0:
                    root.clear()
            elif elem.tag == 'link':
                source_node = str(elem.get('from'))
                terminal_node = str(elem.get('to'))
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
                    None,
                    None,
                    None
                ))
                count += 1
                if count == n:
                    log.debug(f'Parsing link {count}.')
                    n <<= 1
                if count % 100000 == 0:
                    root.clear()

    if count != n << 1:
        log.debug(f'Parsing link {count}.')

    network.close()

    log.info('Writing parsed links and nodes to database.')
    database.insert_values('nodes', nodes, 3)
    database.insert_values('links', links, 12)
    database.connection.commit()

    log.info('Creating indexes on new tables.')
    create_indexes(database)


def main():
    desc = (
        'Parse the MATSim network file and extract the basic node and '
        'link road features and store them in the database. Other road '
        ' relationships (ie regions) are calculated and updated later.'
    )
    parser = ArgumentParser('icarus.parse.roads', description=desc, add_help=False)

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
    logpath = path('logs/parse_roads.log')
    dbpath = path('database.db')
    networkpath = path('input/network.xml.gz')

    handlers = []
    handlers.append(log.StreamHandler())
    handlers.append(log.FileHandler(logpath, 'w'))
    if args.log is not None:
        handlers.append(log.FileHandler(args.log, 'w'))
    log.basicConfig(
        format='%(asctime)s %(levelname)s %(filename)s:%(lineno)s %(message)s',
        level=getattr(log, args.level.upper()),
        handlers=handlers
    )

    log.info('Running roads parsing module.')
    log.info(f'Loading data from {homepath}.')
    log.info('Verifying process metadata/conditions.')

    database = SqliteUtil(dbpath)

    if not ready(networkpath):
        log.error('Process dependencies not met; see warnings and '
            'documentation for more details.')
        exit(1)
    if complete(database) and not args.force:
        log.error('Some or all of this process is already complete.')
        log.error('Would you like to continue? [Y/n]')
        if input().lower() not in ('y', 'yes', 'yeet'):
            exit()
    
    try:
        log.info('Starting roads parsing.')
        parse_roads(database, networkpath, 2223, 2223)
    except:
        log.exception('Critical error while parsing roads; '
            'terminating process and exiting.')
        exit(1)
    

if __name__ == '__main__':
    main()
