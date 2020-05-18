
import os
import logging as log
from argparse import ArgumentParser

from icarus.parse.abm.abm import Abm
from icarus.util.sqlite import SqliteUtil
from icarus.util.config import ConfigUtil

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

log.info('Running MAG ABM parsing tool.')
log.info(f'Loading run data from {home}.')

database = SqliteUtil(path('database.db'))
abm = Abm(database)

trips_file = config['population']['trips_file']
persons_file = config['population']['persons_file']
households_file = config['population']['households_file']

if not abm.ready():
    log.warning('Dependent data not parsed or generated.')
    exit(1)
elif abm.complete():
    log.warning('Population data already parsed. Would you like to replace it? [Y/n]')
    if input().lower() not in ('y', 'yes', 'yeet'):
        log.info('User chose to keep existing population data; exiting parsing tool.')
        exit()

try:
    log.info('Starting population parsing.')
    abm.parse(trips_file, households_file, persons_file)
except:
    log.exception('Critical error while parsing population; '
        'terminating process and exiting.')
    exit(1)