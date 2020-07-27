
import os
import logging as log

from argparse import ArgumentParser
from xml.etree.ElementTree import iterparse
from pyproj.transformer import Transformer

from icarus.util.file import multiopen, exists
from icarus.util.config import ConfigUtil
from icarus.util.sqlite import SqliteUtil


def ready(networkpath: str):
    present = exists(networkpath)
    if not present:
        log.info(f'Could not find file {networkpath}.')
    return present


def complete(database: SqliteUtil):
    tables = ('nodes', 'links')
    exists = database.table_exists(*tables)
    if len(exists):
        present = ', '.join(exists)
        log.info(f'Found tables {present} already in database.')
    return len(exists) > 0


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
                    log.info(f'Parsing node {count}.')
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
                    log.info(f'Parsing node {count}.')
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
                    log.info(f'Parsing link {count}.')
                    n <<= 1
                if count % 100000 == 0:
                    root.clear()

    if count != n << 1:
        log.info(f'Parsing link {count}.')

    network.close()

    log.info('Writing parsed links and nodes to database.')
    database.insert_values('nodes', nodes, 3)
    database.insert_values('links', links, 12)
    database.connection.commit()

    log.info('Creating indexes on new tables.')
    create_indexes(database)


def main():
    parser = ArgumentParser('road network parser')
    
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

    log.info('Running roads parsing tool.')
    log.info(f'Loading run data from {home}.')

    database = SqliteUtil(path('database.db'))
    networkpath = path('input/network.xml.gz')

    if not ready(networkpath):
        log.warning('Dependent data not parsed or generated.')
        log.warning('Roads parsing dependencies include network generation as well '
            'as exposure and regions parsing.')
        exit(1)
    elif complete(database):
        log.warning('Roads already parsed. Would you like to replace it? [Y/n]')
        if input().lower() not in ('y', 'yes', 'yeet'):
            log.info('User chose to keep existing roads; exiting parsing tool.')
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
