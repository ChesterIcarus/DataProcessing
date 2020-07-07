
import os
import csv
import shapefile
import logging as log

from argparse import ArgumentParser
from typing import Dict, Iterable, Tuple
from pyproj.transformer import Transformer
from rtree.index import Index
from shapely.geometry import Point, Polygon
from shapely.wkt import loads, dumps

from icarus.util.sqlite import SqliteUtil
from icarus.util.config import ConfigUtil
from icarus.util.general import counter


class Region:
    __slots__ = ('maz', 'polygon')

    def __init__(self, maz: int, polygon: str):
        self.maz = maz
        self.polygon = Polygon(loads(polygon))


class Parcel:
    __slots__ = ('apn', 'kind', 'cooling', 'polygon', 'maz')

    def __init__(self, apn: str, kind: str, cooling: bool, polygon: Polygon):
        self.apn = apn
        self.kind = kind
        self.cooling = cooling
        self.polygon = polygon
        self.maz = None


def complete(database: SqliteUtil):
    done = False
    exists = database.table_exists('parcels')
    if len(exists):
        log.warning('Database already has table parcels.')
        done = True

    return done


def ready(database: SqliteUtil, residence_file: str, commerce_file:str, 
        parcel_file: str):
    ready = True
    exists = database.table_exists('regions')
    if not len(exists):
        log.warning('Database is missing table regions.')
        ready = False
    files = (residence_file, commerce_file, parcel_file)
    for f in files:
        exists = os.path.exists(f)
        if not exists:
            log.warning(f'Could not open file {f}.')
            ready = False
    
    return ready


def create_tables(database: SqliteUtil):
    database.drop_table('parcels')
    query = '''
        CREATE TABLE parcels(
            apn VARCHAR(255),
            maz SMALLINT UNSIGNED,
            type VARCHAR(255),
            cooling TINYINT UNSIGNED,
            air_temperature INT UNSIGNED,
            mrt_temperature INT UNSIGNED,
            center VARCHAR(255),
            region TEXT
        );
    '''
    database.cursor.execute(query)
    database.connection.commit()


def create_indexes(database: SqliteUtil):
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
    database.connection.commit()


def load_regions(database: SqliteUtil):
    query = '''
        SELECT
            maz,
            region
        FROM regions;
    '''
    database.cursor.execute(query)
    rows = database.fetch_rows()
    rows = counter(rows, 'Loading region %s.')

    regions = []
    for maz, polygon in rows:
        region = Region(maz, polygon)
        regions.append(region)

    return regions


def parse_parcels(database: SqliteUtil, residence_file: str, commerce_file:str, 
        parcel_file: str, cooling_file: str, src_epsg: int, prj_epsg: int):
    boundaries = {}
    cooling = {}
    parcels = []
    apns = set()

    transformer = Transformer.from_crs(f'epsg:{src_epsg}', 
        f'epsg:{prj_epsg}', always_xy=True, skip_equivalent=True)
    project = transformer.transform

    log.info('Allocating tables for parcels.')
    create_tables(database)

    log.info('Parsing parcel boudaries from shapefile.')
    parser = shapefile.Reader(parcel_file)
    iter_boundaries = counter(iter(parser), 'Parsing parcel boundary %s.')
    for parcel in iter_boundaries:
        if len(parcel.shape.points):
            apn = parcel.record['APN']
            points = (project(*pt) for pt in parcel.shape.points)
            polygon = Polygon(points)
            boundaries[apn] = polygon
    parser.close()

    log.info('Loading cooling information from csv file.')
    with open(cooling_file, 'r') as open_file:
            lines = csv.reader(open_file, delimiter=',', quotechar='"')
            next(lines)
            for desc, _, cool in lines:
                cooling[desc] = bool(cool)
    
    log.info('Parsing residential parcels from database file.')
    parser = shapefile.Reader(residence_file)
    iter_parcels = counter(parser.iterRecords(), 'Parsing residential parcel %s.')
    for record in iter_parcels:
        apn = record['APN']
        if apn in boundaries and apn not in apn:
            cool = True
            polygon = boundaries[apn]
            parcel = Parcel(apn, 'residential', cool, polygon)
            parcels.append(parcel)
            apns.add(apn)
    parser.close()
    
    log.info('Parsing comercial parcels from database file.')
    parser = shapefile.Reader(commerce_file)
    iter_parcels = counter(parser.iterRecords(), 'Parsing commercial parcel %s.')
    for record in iter_parcels:
        apn = record['APN']
        if apn in boundaries and apn not in apns:
            desc = record['DESCRIPT']
            cool = cooling[desc]
            polygon = boundaries[apn]
            parcel = Parcel(apn, 'commercial', cool, polygon)
            parcels.append(parcel)
            apns.add(apn)
    parser.close()

    log.info('Parsing extraneous parcels from shapefile.')
    other = set(boundaries.keys()) - apns
    other = counter(other, 'Parsing extraneous parcel %s.')
    for apn in other:
        polygon = boundaries[apn]
        parcel = Parcel(apn, 'other', True, polygon)
        parcels.append(parcel)

    def load():
        for idx, parcel in enumerate(parcels):
            pt = parcel.polygon.centroid
            yield (idx, (pt.x, pt.y, pt.x, pt.y), None)
    
    log.info('Building spatial index from parcel data.')
    index = Index(load())

    log.info('Loading network region data.')
    regions = load_regions(database)

    log.info('Scanning regions and mapping mazs to parcels.')
    iter_regions = counter(regions, 'Sacnning region %s.')
    for region in iter_regions:
        apn = f'maz-{region.maz}'
        parcel = Parcel(apn, 'default', True, region.polygon)
        parcel.maz = region.maz
        parcels.append(parcel)
        result = index.intersection(region.polygon.bounds)
        for idx in result:
            parcel = parcels[idx]
            if region.polygon.contains(parcel.polygon.centroid):
                if parcel.maz is not None:
                    warning = 'Parcel %s is in both region %s and %s' \
                        '; the latter region will be kept.'
                    log.warning(warning % (parcel.apn, parcel.maz, region.maz))
                parcel.maz = region.maz
    del regions

    def dump():
        for parcel in parcels:
            yield (
                parcel.apn,
                parcel.maz,
                parcel.kind,
                int(parcel.cooling),
                None,
                None,
                dumps(parcel.polygon.centroid),
                dumps(parcel.polygon)
            )

    log.info('Writing parsed parcels to database.')
    database.insert_values('parcels', dump(), 8)
    database.connection.commit()

    log.info('Creating indexes on new tables.')
    create_indexes(database)


def main():
    parser = ArgumentParser('parcel parser')
    
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

    log.info('Running parcels parsing tool.')
    log.info(f'Loading run data from {home}.')

    config = ConfigUtil.load_config(path('config.json'))
    database = SqliteUtil(path('database.db'))

    residence_file = config['network']['parcels']['residence_file']
    commerce_file = config['network']['parcels']['commerce_file']
    parcel_file = config['network']['parcels']['parcel_file']
    cooling_file = config['network']['parcels']['type_file']

    if not ready(database, residence_file, commerce_file, parcel_file):
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
        log.info('Starting parcel parsing.')
        parse_parcels(database, residence_file, commerce_file, 
            parcel_file, cooling_file, 2223, 2223)
    except:
        log.exception('Critical error while parsing parcels; '
            'terminating process and exiting.')
        exit(1)


if __name__ == '__main__':
    main()

