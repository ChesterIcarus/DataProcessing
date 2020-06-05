
import os
import logging as log
from argparse import ArgumentParser

from icarus.parse.mrt.mrt import Mrt
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

log.info('Running Maricopa MRT parsing tool.')
log.info(f'Loading run data from {home}.')

database = SqliteUtil(path('database.db'))
mrt = Mrt(database)
mrt_dir = path(config['network']['exposure']['mrt_dir'])

if not mrt.ready():
    log.error('Dependent data not parsed or generated; see warnings.')
    exit(1)
elif mrt.complete():
    log.warning('MRT data already parsed. Would you like to replace it? [Y/n]')
    if input().lower() not in ('y', 'yes', 'yeet'):
        log.info('User chose to keep existing MRT data; exiting parsing tool.')
        exit()

try:
    log.info('Starting MRT parsing.')
    mrt.parse(mrt_dir)
except:
    log.exception('Critical error while parsing MRT; '
        'terminating process and exiting.')
    exit(1)
