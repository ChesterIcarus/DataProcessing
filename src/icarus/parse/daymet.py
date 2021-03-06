
import os
import logging as log

from argparse import ArgumentParser
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
        log.warning(f'Found {nnull}/{null} links with/without air '
            'temperature profiles.')
        done = True
    null, nnull = null_count(database, 'parcels', 'air_temperature')
    if nnull > 0:
        log.warning(f'Found {nnull}/{null} parcels with/without air '
            'temperature profiles.')
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
        (tmax+tmin)/2-(tmax-tmin)/2*cos(pi*(24+tdawn-t)/(24+tdawn-tpeak)))


def create_tables(database: SqliteUtil):
    database.drop_table('air_temperatures', 'temp_links', 'temp_parcels',
        'temp_links_merged', 'temp_parcels_merged')
    query = '''
        CREATE TABLE air_temperatures(
            temperature_id MEDIUMINT UNSIGNED,
            temperature_idx SMALLINT UNSIGNED,
            time MEDIUMINT UNSIGNED,
            temperature FLOAT
        );  
    '''
    database.cursor.execute(query)
    query = '''
        CREATE TABLE temp_links(
            link_id VARCHAR(255),
            air_temperature MEDIUMINT UNSIGNED
        );
    '''
    database.cursor.execute(query)
    query = '''
        CREATE TABLE temp_parcels(
            apn VARCHAR(255),
            air_temperature MEDIUMINT UNSIGNED
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
    query = '''
        CREATE INDEX links_air
        ON links(air_temperature);
    '''
    database.cursor.execute(query)
    query = '''
        CREATE INDEX links_mrt
        ON links(mrt_temperature);
    '''
    database.cursor.execute(query)
    query = '''
        CREATE INDEX parcels_apn
        ON parcels(apn);
    '''
    database.cursor.execute(query)
    query = '''
        CREATE INDEX parcels_maz
        ON parcels(maz);
    '''
    database.cursor.execute(query)
    query = '''
        CREATE INDEX parcels_air
        ON parcels(air_temperature);
    '''
    database.cursor.execute(query)
    query = '''
        CREATE INDEX parcels_mrt
        ON parcels(mrt_temperature);
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
    rows = counter(rows, 'Loading link %s.')

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
    rows = counter(rows, 'Loading parcel %s.')

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
                        log.info(f'Loading air temperature reading {point_count}.')
                        n <<= 1

        tmaxnc.close()
        tminnc.close()
    
    if point_count != n >> 1:
        log.info(f'Loading air temperature reading {point_count}.')
    
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
    iter_links = counter(links, 'Applying profile to link %s.')
    for link in iter_links:
        result = index.nearest((link.x, link.y, link.x, link.y), objects=True)
        profile = next(result).object
        link.air_temperature = profile
        used.add(profile)

    def dump_links():
        for link in links:
            yield (
                link.id,
                link.air_temperature
            )

    log.info('Writing updated links to database.')
    database.insert_values('temp_links', dump_links(), 2)
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
    iter_parcels = counter(parcels, 'Applying profile to parcel %s.')
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
            yield (
                parcel.apn,
                parcel.air_temperature
            )
    
    log.info('Writing updated parcels to database.')
    database.insert_values('temp_parcels', dump_parcels(), 2)
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

    log.info('Merging, dropping and renaming old tables.')

    query = '''
        CREATE INDEX temp_links_link
        ON temp_links(link_id);
    '''
    database.cursor.execute(query)
    query = '''
        CREATE TABLE temp_links_merged
        AS SELECT
            links.link_id,
            links.source_node,
            links.terminal_node,
            links.length,
            links.freespeed,
            links.capacity,
            links.permlanes,
            links.oneway,
            links.modes,
            temp_links.air_temperature,
            links.mrt_temperature
        FROM links
        INNER JOIN temp_links
        USING(link_id);
    '''
    database.cursor.execute(query)
    query = '''
        CREATE INDEX temp_parcels_parcel
        ON temp_parcels(apn);
    '''
    database.cursor.execute(query)
    query = '''
        CREATE TABLE temp_parcels_merged
        AS SELECT
            parcels.apn,
            parcels.maz,
            parcels.type,
            parcels.cooling,
            temp_parcels.air_temperature,
            parcels.mrt_temperature,
            parcels.center,
            parcels.region
        FROM parcels
        INNER JOIN temp_parcels
        USING(apn);
    '''
    database.cursor.execute(query)

    original = database.count_rows('links')
    merged = database.count_rows('temp_links_merged')
    if original != merged:
        log.error('Original links and updated links tables '
            'do not align; quiting to prevent data loss.')
        raise RuntimeError
    else:
        database.drop_table('links', 'temp_links')
        query = '''
            ALTER TABLE temp_links_merged
            RENAME TO links;
        '''
        database.cursor.execute(query)
    
    original = database.count_rows('parcels')
    merged = database.count_rows('temp_parcels_merged')
    if original != merged:
        log.error('Original parcels and updated parcels tables '
            'do not align; quiting to prevent data loss.')
        raise RuntimeError
    else:
        database.drop_table('parcels', 'temp_parcels')
        query = '''
            ALTER TABLE temp_parcels_merged
            RENAME TO parcels;
        '''
        database.cursor.execute(query)
    
    database.connection.commit()

    log.info('Creating indexes on new tables.')
    create_indexes(database)

    log.info('Writing process metadata.')
    

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

    tmin_files = config['network']['exposure']['tmin_files']
    tmax_files = config['network']['exposure']['tmax_files']
    day = config['network']['exposure']['day']
    steps = config['network']['exposure']['steps']

    log.info('Running roads parsing tool.')
    log.info(f'Loading run data from {home}.')

    if not ready(database, tmin_files, tmax_files):
        log.error('Process dependencies not met; see warnings and '
            'docuemntation for more details.')
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
        log.info('Starting road parsing.')
        parse_temperatures(database, tmin_files, tmax_files, 
            steps, day, 4326, 2223)
    except:
        log.exception('Critical error while parsing roads; '
            'terminating process and exiting.')
        exit(1)


if __name__ == '__main__':
    main()
