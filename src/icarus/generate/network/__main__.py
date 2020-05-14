
import os
import logging as log
from argparse import ArgumentParser

from icarus.generate.network.network import Network
from icarus.util.config import ConfigUtil
from icarus.util.sqlite import SqliteUtil

parser = ArgumentParser()
parser.add_argument('--folder', type=str, dest='folder', default='.')
parser.add_argument('--log', type=str, dest='log', default=None)
parser.add_argument('--level', type=str, dest='level', default='info',
    choices=('notset', 'debug', 'info', 'warning', 'error', 'critical'))
args = parser.parse_args()

handlers = []
handlers.append(log.StreamHandler())
if args.log is not None:
    handlers.append(log.FileHandler(args.log, 'w'))
log.basicConfig(
    format='%(asctime)s %(levelname)s %(filename)s:%(lineno)s %(message)s',
    level=getattr(log, args.level.upper()),
    handlers=handlers)

path = lambda x: os.path.abspath(os.path.join(args.folder, x))
home = path('')
config = ConfigUtil.load_config(path('config.json'))

log.info('Running network generation tool.')
log.info(f'Loading run data from {home}.')

database = SqliteUtil(path('database.db'))
population = Network(home)


osm = config['network']['roads']['osm_file']
schedule = config['network']['roads']['schedule_dir']
osmosis = config['network']['roads']['osmosis']
pt2matsim = config['network']['roads']['pt2matsim']
region = config['network']['roads']['region']
epsg = config['network']['epsg']


if not population.ready():
    log.warning('Dependent data not parsed or generated; see warnings for details.')
    exit(1)
elif population.complete():
    log.warning('Network already generated. Would you like to replace it? [Y/n]')
    if input().lower() not in ('y', 'yes', 'yeet'):
        log.info('User chose to keep existing network; exiting generation tool.')
        exit()

try:
    log.info('Starting network generation.')
    population.generate(osm, schedule, region, epsg, pt2matsim, osmosis)
except:
    log.exception('Critical error while generating network; '
        'terminating process and exiting.')
    exit(1)

database.close()