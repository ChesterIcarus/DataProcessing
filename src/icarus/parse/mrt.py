
from __future__ import annotations

import os
import csv
import logging as log

from glob import glob
from math import sqrt
from typing import List, Dict, FrozenSet, Tuple
from argparse import ArgumentParser, SUPPRESS
from pyproj.transformer import Transformer
from rtree.index import Index

from icarus.util.general import counter
from icarus.util.sqlite import SqliteUtil
from icarus.util.config import ConfigUtil


class Point:
    __slots__ = ('id', 'x', 'y', 'mrt', 'pet', 'utci')

    def __init__(self, uuid: int, x: float, y: float, mrt: float, 
            pet: float, utci: float):
        self.id = uuid
        self.x = x
        self.y = y
        self.mrt = mrt
        self.pet = pet
        self.utci = utci

    def entry(self):
        return (self.id, (self.x, self.y, self.x, self.y), None)


class Link:
    __slots__ = ('id', 'source_node', 'terminal_node', 'lanes', 'freespeed',
            'profile')

    def __init__(self, uuid: str, source_node: Node, terminal_node: Node, 
            lanes: float, freespeed: float):
        self.id = uuid
        self.source_node = source_node
        self.terminal_node = terminal_node
        self.lanes = lanes
        self.freespeed = freespeed
        self.profile = None


    def bounds(self, buffer: float = 0):
        xmin = min(self.source_node.x, self.terminal_node.x) - buffer
        xmax = max(self.source_node.x, self.terminal_node.x) + buffer
        ymin = min(self.source_node.y, self.terminal_node.y) - buffer
        ymax = max(self.source_node.y, self.terminal_node.y) + buffer
        
        return (xmin, ymin, xmax, ymax)


class Node:
    __slots__ = ('id', 'maz', 'x', 'y')

    def __init__(self, uuid: str, x: float, y: float):
        self.id = uuid
        self.x = x
        self.y = y


def null_count(database: SqliteUtil, table: str, col: str):
    query = f'''
        SELECT
            CASE 
                WHEN {col} IS NULL 
                THEN 0 ELSE 1 
                END AS valid,
            COUNT(*) AS freq
        FROM {table}
        GROUP BY valid;
    '''
    database.cursor.execute(query)
    rows = database.fetch_rows()
    
    null, nnull = 0, 0
    for value, freq in rows:
        if value == 0:
            null = freq
        elif value == 1:
            nnull = freq

    return null, nnull


def complete(database: SqliteUtil):
    complete = False
    present = database.table_exists('mrt_temperatures')
    _, nnull = null_count(database, 'links', 'mrt_temperature')
    if present:
        log.warning('Table mrt_temperatures already exists.')
        complete = True
    if nnull:
        log.warning(f'{nnull} links already have temperature profiles.')
        complete = True

    return complete


def ready(database: SqliteUtil):
    ready = True
    tables = set(('links', 'nodes'))
    present = set(database.table_exists(*tables))
    missing = tables - present
    for table in missing:
        log.warning(f'Table {table} is missing.')
        ready = False

    return ready


def xy(point: str) -> tuple:
    return tuple(map(float, point[7:-1].split(' ')))


def hhmm_to_secs(hhmm: str) -> int:
    hrs, mins, ampm = hhmm.upper().replace(' ', ':').split(':')
    return (int(hrs) % 12) * 3600 + int(mins) * 60 + (ampm == 'PM') * 43200


def create_tables(database: SqliteUtil):
    database.drop_table('mrt_temperatures')
    query = '''
        CREATE TABLE mrt_temperatures(
            temperature_id MEDIUMINT UNSIGNED,
            temperature_idx SMALLINT UNSIGNED,
            time MEDIUMINT UNSIGNED,
            mrt FLOAT,
            pet FLOAT,
            utci FLOAT
        );
    '''
    database.cursor.execute(query)
    database.connection.commit()


def create_indexes(database: SqliteUtil):
    query = '''
        CREATE INDEX mrt_temperatures_temperature
        ON mrt_temperatures(temperature_id, temperature_idx); 
    '''
    database.cursor.execute(query)
    query = '''
        CREATE INDEX links_mrt_temperature
        ON links(mrt_temperature); 
    '''
    database.cursor.execute(query)
    database.connection.commit()


def load_nodes(database: SqliteUtil) -> Dict[str,Node]:
    query = '''
        SELECT
            node_id,
            point
        FROM nodes;
    '''
    database.cursor.execute(query)
    rows = database.fetch_rows()
    rows = counter(rows, 'Loading node %s.', level=log.DEBUG)

    nodes: Dict[str,Node] = {}
    for uuid, point in rows:
        x, y = xy(point)
        node = Node(uuid, x, y)
        nodes[uuid] = node
    
    return nodes


def load_links(database: SqliteUtil, nodes: Dict[str,Node]) -> Dict[str,Link]:
    query = '''
        SELECT
            link_id,
            source_node,
            terminal_node,
            freespeed,
            permlanes
        FROM links;
    '''
    database.cursor.execute(query)
    rows = database.fetch_rows()
    rows = counter(rows, 'Loading link %s.', level=log.DEBUG)

    links: Dict[str,Link] = {}
    for uuid, src, term, speed, lanes in rows:
        source_node = nodes[src]
        terminal_node = nodes[term]
        link = Link(uuid, source_node, terminal_node, lanes, speed)
        links[uuid] = link

    return links


def parse_points(csvfile: str, src_epsg: int, prj_epsg: int) \
            -> Tuple[List[Point],int]:
    log.debug(f'Opening {csvfile}.')
    csv_file = open(csvfile, 'r')
    iter_points = csv.reader(csv_file, delimiter=',', quotechar='"')
    next(iter_points)
    iter_points = counter(iter_points, 'Parsing point %s.', level=log.DEBUG)

    transformer = Transformer.from_crs(f'epsg:{src_epsg}', 
        f'epsg:{prj_epsg}', always_xy=True, skip_equivalent=True)
    project = transformer.transform

    points = []
    peek = next(iter_points)
    iter_points.send(peek)
    secs = hhmm_to_secs(peek[2])
    for uuid, (lat, lon, _, mrt, pet, utci) in enumerate(iter_points):
        x, y = project(lon, lat)
        point = Point(uuid, x, y, float(mrt), float(pet), float(utci))
        points.append(point)

    csv_file.close()

    return points, secs


def parse_temperatures(csvfile: str) \
            -> Tuple[List[Tuple[float,float,float]],int]:
    log.debug(f'Opening {csvfile}.')
    csv_file = open(csvfile, 'r')
    iter_temps = csv.reader(csv_file, delimiter=',', quotechar='"')
    next(iter_temps)
    iter_temps = counter(iter_temps, 'Parsing temperature %s.', level=log.DEBUG)

    temps = []
    peek = next(iter_temps)
    iter_temps.send(peek)
    secs = hhmm_to_secs(peek[2])
    for _, _, _, mrt, pet, utci in iter_temps:
        temps.append((float(mrt), float(pet), float(utci)))
        
    csv_file.close()

    return temps, secs


def parse_mrt(database: SqliteUtil, path: str, src_epsg: int, prj_epsg: int,
        bounds:int = 30, steps: int = 96):
    log.info('Allocating tables for MRT temperature profiles.')
    create_tables(database)

    log.info('Loading network nodes from database.')
    nodes: Dict[str,Node]
    nodes = load_nodes(database)

    log.info('Loading network links from database.')
    links: Dict[str,Link] 
    links= load_links(database, nodes)

    log.info(f'Searching for mrt files in {path}.')
    csvfiles = glob(f'{path}/**/*.csv', recursive=True)
    total = len(csvfiles)
    csvfiles = iter(csvfiles)

    log.info(f'Parsing temperatures from mrt file 1 of {total}.')
    points: List[Point]
    time: int 
    points, time = parse_points(next(csvfiles), src_epsg, prj_epsg)
    
    log.info('Building spatial index on MRT points.')
    index = Index((point.entry() for point in points))

    log.info('Scanning link bounds and building profiles.')
    mapping: Dict[FrozenSet[int],int] = {}
    count = 0
    empty = 0
    iter_links = counter(links.values(), 'Scanning link %s.', level=log.DEBUG)
    for link in iter_links:
        d = link.terminal_node.x * link.source_node.y - \
            link.source_node.x * link.terminal_node.y
        dx = link.terminal_node.x - link.source_node.x
        dy = link.terminal_node.y - link.source_node.y
        l = sqrt(dy * dy + dx * dx)

        nearby = index.intersection(link.bounds(bounds))
        contained = []
        for uuid in nearby:
            point = points[uuid]
            x = point.x
            y = point.y
            if l > 0:
                dist = abs(dy * x - dx * y + d ) / l
            else:
                px = point.x - link.source_node.x
                py = point.y - link.source_node.y
                dist = sqrt(px * px + py * py)
            if dist <= bounds:
                contained.append(point.id)
        
        if contained:
            profile = frozenset(contained)
            if profile in mapping:
                link.profile = mapping[profile]
            else:
                mapping[profile] = count
                link.profile = count
                count += 1
        else:
            empty += 1

    profiles: List[Tuple[int]]
    profiles = [tuple(key) for key in mapping.keys()]

    if empty:
        log.warning(f'Found {empty} links without any MRT temperature profile.')

    def dump_points():
        idx = time // (86400 // steps)
        for uuid, profile in enumerate(profiles):
            mrt, pet, utci = 0, 0, 0
            count = len(profile)
            for ptid in profile:
                point = points[ptid]
                mrt += point.mrt
                pet += point.pet
                utci += point.utci
            yield (uuid, idx, time, mrt / count, pet / count, utci / count)

    def dump_links():
        for link in links.values():
            yield (link.profile, link.id)

    log.info('Writing profiles to dataabse.')

    query = '''
        UPDATE links
        SET mrt_temperature = :profile
        WHERE link_id = :id;
    '''
    database.insert_values('mrt_temperatures', dump_points(), 6)
    database.cursor.executemany(query, dump_links())
    database.connection.commit()

    del links, nodes, index, mapping, points

    log.info('Handling remaining temperatures with defined profile.')

    def dump_temperaures(time: int, temperatures: List[Tuple[float,float,float]]):
        idx = time // (86400 // steps)
        for uuid, profile in enumerate(profiles):
            mrt, pet, utci = 0, 0, 0
            count = len(profile)
            for tempid in profile:
                temp = temperatures[tempid]
                mrt += temp[0]
                pet += temp[1]
                utci += temp[2]
            yield (uuid, idx, time, mrt / count, pet / count, utci / count)

    for idx, csvfile in enumerate(csvfiles, 2):
        log.info(f'Parsing temperature file {idx} of {total}')
        time: int
        temperatures: List[Tuple[float,float,float]]
        temperatures, time = parse_temperatures(csvfile)

        log.debug('Writing temperature data to database.')
        database.insert_values('mrt_temperatures', 
            dump_temperaures(time, temperatures), 6)
        database.connection.commit()

    log.info('Creating indexes on new/updated tables.')
    create_indexes(database)


def main():
    desc = (
        'Parse the Maricopa MRT temperature data. This process will first '
        'parse one file to extract the temperature locations, map each '
        'link to a set of temperature locations and build temperature '
        'profiles. Then the remaining data will parsed and averaged for '
        'each temperature profile. There will only be as many profiles as '
        'links and likely at least half as many.'
    )
    parser = ArgumentParser('icarus.parse.mrt', description=desc, add_help=False)
    
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

    configuration = parser.add_argument_group('configuration options')
    configuration.add_argument('--source-epsg', type=int, dest='src_epsg', 
        default=4326, help='epsg projection the mrt data is in')
    configuration.add_argument('--project-epsg', type=int, dest='prj_epsg', 
        default=2223, help='epsg projection to convert the mrt data to')
    configuration.add_argument('--bounds', type=float, dest='bounds', default=50,
        help='range around each link to scan for mrt points')
    configuration.add_argument('--steps', type=int, dest='steps', default=96,
        help='number of temperature readings in a 24-hour period ')
        
    args = parser.parse_args()

    path = lambda x: os.path.abspath(os.path.join(args.dir, x))
    os.makedirs(path('logs'), exist_ok=True)
    homepath = path('')
    logpath = path('logs/parse_mrt.log')
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

    log.info('Running mrt parsing module.')
    log.info(f'Loading data from {homepath}.')
    log.info('Verifying process metadata/conditions.')

    database = SqliteUtil(dbpath)
    config = ConfigUtil.load_config(configpath)

    mrtpath = config['network']['exposure']['mrt_dir']

    if not ready(database):
        log.error('Process dependencies not met; see warnings and '
            'documentation for more details.')
        exit(1)
    if complete(database) and not args.force:
        log.error('Some or all of this process is already complete.')
        log.error('Would you like to continue? [Y/n]')
        if input().lower() not in ('y', 'yes', 'yeet'):
            exit()

    try:
        log.info('Starting mrt temperature parsing.')
        parse_mrt(
            database, 
            mrtpath, 
            src_epsg=args.src_epsg,
            prj_epsg=args.prj_epsg, 
            bounds=args.bounds,
            steps=args.steps
        )
    except:
        log.exception('Critical error while running mrt temperature '
            'parsing; cleaning up and terminating.')
        exit(1)


if __name__ == '__main__':
    main()
