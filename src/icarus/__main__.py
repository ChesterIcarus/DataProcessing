
import sys
import os
import logging as log

from argparse import ArgumentParser

from icarus.network.regions import Regions
from icarus.network.exposure import Exposure
from icarus.network.roads import Roads
from icarus.network.parcels import Parcels
from icarus.util.config import ConfigUtil
from icarus.util.sqlite import SqliteUtil


parser = ArgumentParser()
parser.add_argument('--folder', type=str, dest='folder', default='.')
parser.add_argument('--log', type=str, dest='log', default=None)
parser.add_argument('--level', type=str, dest='level', default='info',
    choices=('notset', 'debug', 'info', 'warning', 'error', 'critical'))
subparsers = parser.add_subparsers(dest='command')

parser_parse = subparsers.add_parser('parse', help='parse help')
parser_parse.add_argument('--source', type=str, nargs='?', dest='source',
    default=('roads', 'exposure', 'regions', 'parcels', 'population'),
    choices=('roads', 'exposure', 'regions', 'parcels', 'population'))
parser_parse.add_argument('--replace', dest='replace', action='store_true', 
    default=False)

parser_generate = subparsers.add_parser('generate', help='generate help')
parser_generate.add_argument('--replace', dest='replace', action='store_true', 
    default=False)

parser_validate = subparsers.add_parser('validate', help='validate help')

args = parser.parse_args()

handlers = []
handlers.append(log.StreamHandler())
if args.log is not None:
    handlers.append(log.FileHandler(args.log, 'w'))
log.basicConfig(
    format='%(asctime)s %(levelname)s %(filename)s:%(lineno)s %(message)s',
    level=getattr(log, args.level.upper()),
    handlers=handlers)

path = lambda x: os.path.join(args.folder, x)
config = ConfigUtil.load_config(path('config.json'))
database = SqliteUtil('database.db')

if args.command == 'parse':
    if 'regions' in args.source:
        regions = Regions(database)
        complete = len(regions.database.table_exists('regions'))
        if complete == 1 and not args.replace:
            log.info(f'Regions already parsed; skipping parsing.')
        else:
            log.info(f'Parsing region data from maricopa region code data.')
            regions.parse(config['network']['regions']['region_file'])
    if 'exposure' in args.source:
        exposure = Exposure(database)
        complete = len(exposure.database.table_exists('centroids', 'temperatures'))
        if complete == 2 and not args.replace:
            log.info(f'Exposure already parsed; skipping parsing.')
        else:
            log.info(f'Parsing exposure data from daymet data.')
            exposure.parse(
                config['network']['exposure']['tmin_files'], 
                config['network']['exposure']['tmax_files'], 
                config['network']['exposure']['steps'],
                config['network']['exposure']['day'])
    if 'roads' in args.source:
        roads = Roads(database)
        complete = len(roads.database.table_exists('links', 'nodes'))
        if complete == 2 and not args.replace:
            log.info(f'Roads already parsed; skipping parsing.')
        else:
            log.info(f'Parsing road data from openstreet map data.')
            roads.parse(
                config['network']['roads']['osm_file'],
                config['network']['roads']['schedule_dir'],
                config['network']['roads']['region'],
                config['network']['epsg'],
                config['network']['roads']['pt2matsim'],
                config['network']['roads']['osmosis'])
    if 'parcels' in args.source:
        parcels = Parcels(database)
        complete = len(parcels.database.table_exists('parcels'))
        if complete == 1 and not args.replace:
            log.info(f'Parcels already parsed; skipping parsing.')
        else:
            log.info('Parsing exposure data from maricopa parcel data.')
            parcels.parse(
                config['network']['parcels']['residence_file'],
                config['network']['parcels']['commerce_file'],
                config['network']['parcels']['parcel_file'])
    
log.info('Everyhing finished; closing module execution.')
database.close()
