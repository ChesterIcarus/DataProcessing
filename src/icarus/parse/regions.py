
import os
import shapefile
import logging as log

from argparse import ArgumentParser
from typing import Tuple
from rtree.index import Index
from shapely.geometry import Polygon, Point
from pyproj import Transformer
from shapely.wkt import dumps

from icarus.util.config import ConfigUtil
from icarus.util.general import counter
from icarus.util.iter import pair
from icarus.util.sqlite import SqliteUtil


def create_tables(database: SqliteUtil):
    database.drop_table('regions')
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
    database.connection.commit()


def parse_regions(database: SqliteUtil, regions_file: str, src_epsg: int, 
        prj_epsg: int):

    log.info('Allocating tables for regions.')
    create_tables(database)

    transformer = Transformer.from_crs(f'epsg:{src_epsg}', 
        f'epsg:{prj_epsg}', always_xy=True, skip_equivalent=True)
    project = transformer.transform

    log.info('Parsing regions from shapefile.')
    parser = shapefile.Reader(regions_file)
    iter_regions = counter(iter(parser), 'Parsing region %s.')
    regions = []
    for item in iter_regions:
        points = (project(*point) for point in item.shape.points)
        polygon = Polygon(points)
        
        regions.append((
            item.record.MAZ_ID_10,
            item.record.TAZ_2015,
            item.record.Sq_miles,
            dumps(polygon.centroid),
            dumps(polygon)
        ))

    parser.close()
    
    log.info('Writing parsed regions to database.')
    database.insert_values('regions', regions, 5)
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

    try:
        log.info('Starting regions parsing.')
        parse_regions(database, regions_file, 2223, 2223)
    except:
        log.exception('Critical error while parsing regions; '
            'terminating process and exiting.')
        exit(1)


if __name__ == '__main__':
    main()
