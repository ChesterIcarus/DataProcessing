
import os
import logging as log
from argparse import ArgumentParser

from icarus.parse.daymet.daymet import Daymet
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

log.info('Running daymet exposure parsing tool.')
log.info(f'Loading run data from {home}.')

database = SqliteUtil(path('database.db'))
daymet = Daymet(database)

tmin_files = config['network']['exposure']['tmin_files']
tmax_files = config['network']['exposure']['tmax_files']
day = config['network']['exposure']['day']
steps = config['network']['exposure']['steps']

if not daymet.ready(tmin_files, tmax_files):
    log.warning('Dependent data not parsed or generated.')
    exit(1)
elif daymet.complete():
    log.warning('Daymet data already parsed. Would you like to replace it? [Y/n]')
    if input().lower() not in ('y', 'yes', 'yeet'):
        log.info('User chose to keep existing daymet data; exiting parsing tool.')
        exit()

try:
    log.info('Starting daymet data parsing.')
    daymet.parse(tmin_files, tmax_files, steps, day)
except:
    log.exception('Critical error while parsing daymet data; '
        'terminating process and exiting.')
    exit(1)