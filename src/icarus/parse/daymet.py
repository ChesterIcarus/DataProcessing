
import os
import logging as log

from argparse import ArgumentParser, SUPPRESS
from typing import List, Callable
from netCDF4 import Dataset             # pylint: disable=no-name-in-module
from pyproj import Transformer
from rtree.index import Index
from math import cos, pi

from icarus.util.sqlite import SqliteUtil
from icarus.util.config import ConfigUtil
from icarus.util.general import counter


class Point:
    __slots__ = ('id', 'x', 'y', 'profile')

    def __init__(self, uuid: int, x: float, y: float, profile: int):
        self.id = uuid
        self.x = x
        self.y = y
        self.profile = profile
    

class Link:
    __slots__ = ('id', 'x', 'y', 'air_temperature')

    def __init__(self, uuid: str, x: int, y: int):
        self.id = uuid
        self.x = x
        self.y = y
        self.air_temperature = None


class Parcel:
    __slots__ = ('apn', 'x', 'y', 'kind', 'cooling', 'air_temperature')
    
    def __init__(self, apn: str, kind: str, cooling: bool, x: float, y: float):
        self.apn = apn
        self.x = x
        self.y = y
        self.kind = kind
        self.cooling = cooling
        self.air_temperature = None


def null_count(database: SqliteUtil, table: str, col: str):
    query = f'''
        SELECT
            CASE 
                WHEN {col} IS NULL 
                THEN 0 ELSE 1 
                END AS valid,
            COUNT(*) AS freq
        FROM {table}
        GROUP BY valid
        ORDER BY valid ASC;
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
    done = False
    exists = database.table_exists('air_temperatures')
    if len(exists):
        log.warning(f'Database already has table air_temperatures.')
        done = True
    null, nnull = null_count(database, 'links', 'air_temperature')
    if nnull > 0:
        perc = round(100 * nnull / (nnull + null), 2)
        log.warning(f'Found {perc}% of links with air temperature profiles already.')
        done = True
    null, nnull = null_count(database, 'parcels', 'air_temperature')
    if nnull > 0:
        perc = round(100 * nnull / (nnull + null), 2)
        log.warning(f'Found {perc}% of parcels with air temperature profiles already.')
        done = True
    
    return done
    

def ready(database: SqliteUtil, tmin_files: List[str], tmax_files: List[str]):
    ready = True
    for t_file in tmin_files + tmax_files:
        exists = os.path.exists(t_file)
        if not exists:
            log.warning(f'Could not open file {t_file}.')
            ready = False
    tables = ('parcels', 'links', 'nodes')
    exists = database.table_exists(*tables)
    missing = set(tables) - set(exists)
    for table in missing:
        log.warning(f'Database is missing table {table}.')
        ready = False    

    return ready


def xy(point: str) -> tuple:
    return tuple(map(float, point[7:-1].split(' ')))


def iterpolation(tmin: float, tmax: float, tdawn: float, tpeak: float):
    return lambda t: (
        (tmax+tmin)/2-(tmax-tmin)/2*cos(pi*(tdawn-t)/(24+tdawn-tpeak)) 
            if t < tdawn else 
        (tmax+tmin)/2+(tmax-tmin)/2*cos(pi*(tpeak-t)/(tpeak-tdawn))
            if t < tpeak else 
        (tmax+tmin)/2-(tmax-tmin)/2*cos(pi*(24+tdawn-t)/(24+tdawn-tpeak))
    )


def create_tables(database: SqliteUtil):
    database.drop_table('air_temperatures')
    database.drop_index('parcels_air_temperature', 'links_air_temperature')
    query = '''
        CREATE TABLE air_temperatures(
            temperature_id MEDIUMINT UNSIGNED,
            temperature_idx SMALLINT UNSIGNED,
            time MEDIUMINT UNSIGNED,
            temperature FLOAT
        );  
    '''
    database.cursor.execute(query)
    database.connection.commit()


def create_indexes(database: SqliteUtil):
    query = '''
        CREATE INDEX air_temperatures_temperature
        ON air_temperatures(temperature_id, temperature_idx); 
    '''
    database.cursor.execute(query)
    query = '''
        CREATE INDEX links_air_temperature
        ON links(air_temperature);
    '''
    database.cursor.execute(query)
    query = '''
        CREATE INDEX parcels_air_temperature
        ON parcels(air_temperature);
    '''
    database.cursor.execute(query)
    database.connection.commit()


def load_links(database: SqliteUtil):
    query = '''
        SELECT
            links.link_id,
            nodes.point
        FROM links
        INNER JOIN nodes
        ON links.source_node = nodes.node_id;
    '''
    database.cursor.execute(query)
    rows = database.fetch_rows()
    rows = counter(rows, 'Loading link %s.', level=log.DEBUG)

    links = []
    for link_id, point in rows:
        x, y = xy(point)
        link = Link(link_id, x, y)
        links.append(link)

    return links


def load_parcels(database: SqliteUtil):
    query = '''
        SELECT
            apn,
            type,
            cooling,
            center
        FROM parcels;
    '''
    database.cursor.execute(query)
    rows = database.fetch_rows()
    rows = counter(rows, 'Loading parcel %s.', level=log.DEBUG)

    parcels = []
    for apn, kind, cooling, center in rows:
        x, y = xy(center)
        parcel = Parcel(apn, kind, bool(cooling), x, y)
        parcels.append(parcel)

    return parcels


def parse_temperatures(database: SqliteUtil, tmin_files: List[str], 
        tmax_files: List[str], steps: int, day: int, src_epsg: int, 
        prj_epsg: int):

    log.info('Allocating tables for air temperatures.')
    create_tables(database)

    files = zip(tmax_files, tmin_files)
    profile_count = 0
    point_count = 0
    temperatures = []
    points = []
    profiles = {}
    n = 1

    transformer = Transformer.from_crs(f'epsg:{src_epsg}', 
        f'epsg:{prj_epsg}', always_xy=True, skip_equivalent=True)
    project = transformer.transform

    def apply(id: int, temp: Callable):
        for step in range(steps):
            prop = step / steps
            row = (id, step, int(86400 * prop), temp(24 * prop))
            yield row

    log.info('Loading temperatures from netCDF4 files.')
    for tmax_file, tmin_file in files:
        tmaxnc = Dataset(tmax_file, 'r')
        tminnc = Dataset(tmin_file, 'r')

        lons = tmaxnc.variables['lon']
        lats = tmaxnc.variables['lat']
        shape = tmaxnc.variables['tmax'].shape

        tmaxs = tmaxnc.variables['tmax'][day]
        tmins = tminnc.variables['tmin'][day]

        for i in range(shape[1]):
            for j in range(shape[2]):
                tmax = tmaxs[i][j]
                tmin = tmins[i][j]

                if tmax != -9999.0:
                    x, y = project(lons[i][j], lats[i][j])
                    idx = f'{tmax}-{tmin}'

                    if idx not in profiles:
                        temp = iterpolation(tmin, tmax, 5, 15)
                        temperatures.extend(apply(profile_count, temp))
                        profiles[idx] = profile_count
                        profile_count += 1
                    
                    profile = profiles[idx]
                    point = Point(point_count, x, y, profile)
                    points.append(point)
                    point_count += 1

                    if point_count == n:
                        log.debug(f'Loading air temperature reading {point_count}.')
                        n <<= 1

        tmaxnc.close()
        tminnc.close()
    
    if point_count != n >> 1:
        log.debug(f'Loading air temperature reading {point_count}.')
    
    def load():
        for point in points:
            x, y = point.x, point.y
            yield (point.id, (x, y, x, y), point.profile)

    log.info('Starting network update for air temperatures.')
    log.info('Building spatial index from temperature profile locations.')
    index = Index(load())
    used = set()
    
    log.info('Loading network links.')
    links = load_links(database)

    log.info('Applying temperature profiles to links.')
    iter_links = counter(links, 'Applying profile to link %s.', level=log.DEBUG)
    for link in iter_links:
        result = index.nearest((link.x, link.y, link.x, link.y), objects=True)
        profile = next(result).object
        link.air_temperature = profile
        used.add(profile)

    def dump_links():
        for link in links:
            yield (link.air_temperature, link.id)

    log.info('Writing updated links to database.')
    query = '''
        UPDATE links
        SET air_temperature = :air_temperature
        WHERE link_id = :link_id;
    '''
    database.connection.executemany(query, dump_links())
    database.connection.commit()
    del links

    log.info('Loading network parcels.')
    parcels = load_parcels(database)

    residential = profile_count
    temperatures.extend(apply(profile_count, lambda x: 26.6667))
    profile_count += 1
    commercial = profile_count
    temperatures.extend(apply(profile_count, lambda x: 26.6667))
    profile_count += 1
    other = profile_count
    temperatures.extend(apply(profile_count, lambda x: 26.6667))
    profile_count += 1
    used.add(residential)
    used.add(commercial)
    used.add(other)

    log.info('Applying temperature profiles to parcels.')
    iter_parcels = counter(parcels, 'Applying profile to parcel %s.', 
        level=log.DEBUG)
    for parcel in iter_parcels:
        if not parcel.cooling:
            x, y = xy(parcel.center)
            result = index.nearest((x, y, x, y), objects=True)
            profile = next(result).object
            parcel.air_temperature = profile
            used.add(profile)
        elif parcel.kind == 'residential':
            parcel.air_temperature = residential
        elif parcel.kind == 'commercial':
            parcel.air_temperature = commercial
        else:
            parcel.air_temperature = other

    def dump_parcels():
        for parcel in parcels:
            yield (parcel.air_temperature, parcel.apn)
    
    log.info('Writing updated parcels to database.')

    query = '''
        UPDATE parcels
        SET air_temperature = :air_temperature
        WHERE apn = :apn;
    '''
    database.cursor.executemany(query, dump_parcels())
    database.connection.commit()
    del parcels

    def dump_temperatures():
        for temp in temperatures:
            if temp[0] in used:
                yield temp

    log.info('Writing parsed air temperatures to database.')
    database.insert_values('air_temperatures', dump_temperatures(), 4)
    database.connection.commit()
    del temperatures

    log.info('Creating indexes on new tables.')
    create_indexes(database)


def main():
    desc = (
        ''
    )
    parser = ArgumentParser('icarus.parse.daymet', description=desc, add_help=False)

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
    logpath = path('logs/parse_daymet.log')
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

    log.info('Running daymet parsing module.')
    log.info(f'Loading data from {homepath}.')
    log.info('Verifying process metadata/conditions.')

    config = ConfigUtil.load_config(configpath)
    database = SqliteUtil(dbpath)

    tmin_files = config['network']['exposure']['tmin_files']
    tmax_files = config['network']['exposure']['tmax_files']
    day = config['network']['exposure']['day']
    steps = config['network']['exposure']['steps']

    if not ready(database, tmin_files, tmax_files):
        log.error('Process dependencies not met; see warnings and '
            'documentation for more details.')
        exit(1)
    if complete(database) and not args.force:
        log.error('Some or all of this process is already complete.')
        log.error('Would you like to continue? [Y/n]')
        if input().lower() not in ('y', 'yes', 'yeet'):
            exit()

    try:
        log.info('Starting road parsing.')
        parse_temperatures(database, tmin_files, tmax_files, 
            steps, day, 4326, 2223)
    except:
        log.exception('Critical error while parsing roads; '
            'terminating process and exiting.')
        exit(1)


if __name__ == '__main__':
    main()
