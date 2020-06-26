
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

    def __init__(self, id: int, x: float, y: float, profile: int):
        self.id = id
        self.x = x
        self.y = y
        self.profile = profile
    

class Link:
    __slots__ = ('id', 'source_node', 'terminal_node', 'length', 'freespeed', 
        'capacity', 'permlanes', 'oneway', 'modes', 'air_temperature', 
        'mrt_temperature', 'x', 'y')

    def __init__(self, id: str, source_node: str, terminal_node: str,
            length: float, freespeed: float, capacity: float, permlanes: float,
            oneway: int, modes: str, air_temperature: int, mrt_temperature: int,
            x: int, y: int):
        self.id = id
        self.source_node = source_node
        self.terminal_node = terminal_node
        self.length = length
        self.freespeed = freespeed
        self.capacity = capacity
        self.permlanes = permlanes
        self.oneway = oneway
        self.modes = modes
        self.air_temperature = air_temperature
        self.mrt_temperature = mrt_temperature
        self.x = x
        self.y = y


class Parcel:
    __slots__ = ('apn', 'maz', 'kind', 'cooling', 'air_temperature', 
        'mrt_temperature', 'center', 'region')
    
    def __init__(self, apn: str, maz: int, kind: str, cooling: bool,
            air_temperature: int, mrt_temperature: int, center: str,
            region: str):
        self.apn = apn
        self.maz = maz
        self.kind = kind
        self.cooling = cooling
        self.air_temperature = air_temperature
        self.mrt_temperature = mrt_temperature
        self.center = center
        self.region = region


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
    database.drop_table('air_temperatures', 'temp_links')
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
    database.connection.commit()


def load_links(database: SqliteUtil):
    query = '''
        SELECT
            links.link_id,
            links.source_node,
            links.terminal_node,
            links.length,
            links.freespeed,
            links.capacity,
            links.permlanes,
            links.oneway,
            links.modes,
            links.air_temperature,
            links.mrt_temperature,
            nodes.point
        FROM links
        INNER JOIN nodes
        ON links.source_node = nodes.node_id;
    '''
    database.cursor.execute(query)
    rows = database.fetch_rows()
    rows = counter(rows, 'Loading link %s.')

    links = []
    for row in rows:
        x, y = xy(row[-1])
        link = Link(*row[:-1], x, y)
        links.append(link)

    return links


def load_parcels(database: SqliteUtil):
    query = '''
        SELECT
            apn,
            maz,
            type,
            cooling,
            air_temperature,
            mrt_temperature,
            center,
            region
        FROM parcels;
    '''
    database.cursor.execute(query)
    rows = database.fetch_rows()
    rows = counter(rows, 'Loading parcel %s.')

    parcels = []
    for row in rows:
        parcel = Parcel(*row)
        parcel.air_temperature = None
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
                link.source_node, 
                link.terminal_node, 
                link.length, 
                link.freespeed, 
                link.capacity, 
                link.permlanes, 
                link.oneway, 
                link.modes, 
                link.air_temperature, 
                link.mrt_temperature
            )

    log.info('Writing updated links to database.')
    query = 'DELETE FROM links;'
    database.cursor.execute(query)
    database.insert_values('links', dump_links(), 11)
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
                parcel.maz,
                parcel.kind,
                parcel.cooling,
                parcel.air_temperature,
                parcel.mrt_temperature,
                parcel.center,
                parcel.region
            )
    
    log.info('Writing updated parcels to database.')
    query = 'DELETE FROM parcels;'
    database.cursor.execute(query)
    database.insert_values('parcels', dump_parcels(), 8)
    database.connection.commit()
    del parcels

    def dump_temperatures():
        for temp in temperatures:
            if temp[0] in used:
                yield temp

    log.info('Writing parsed air temperatures to database.')
    database.insert_values('air_temperatures', dump_temperatures(), 4)
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

    try:
        log.info('Starting roads parsing.')
        parse_temperatures(database, tmin_files, tmax_files, 
            steps, day, 4326, 2223)
    except:
        log.exception('Critical error while parsing roads; '
            'terminating process and exiting.')
        exit(1)


if __name__ == '__main__':
    main()
