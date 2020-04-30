
import os
import logging as log
from argparse import ArgumentParser

from icarus.generate.plans.plans import Plans
from icarus.util.config import ConfigUtil
from icarus.util.sqlite import SqliteUtil

parser = ArgumentParser()
parser.add_argument('--folder', type=str, dest='folder', default='.')
parser.add_argument('--log', type=str, dest='log', default=None)
parser.add_argument('--level', type=str, dest='level', default='info',
    choices=('notset', 'debug', 'info', 'warning', 'error', 'critical'))
parser.add_argument('--replace', dest='replace', action='store_true', default=False)
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
modes = config['simulation']['modes']
conditions = config['simulation']['sample']
planspath = path('input/plans.xml.gz')
vehiclespath = path('input/vehicles.xml.gz')

log.info('Running population generation tool.')
log.info(f'Loading run data from {home}.')

database = SqliteUtil(path('database.db'))
plans = Plans(database)


if not plans.ready():
    log.warning('Dependent data not parsed or generated.')
    log.warning('Input plans depend on population generation.')
    exit(1)
elif plans.complete(planspath, vehiclespath):
    log.warning('Input plans already generated. Would you like to replace it? [Y/n]')
    if input().lower() not in ('y', 'yes', 'yeet'):
        log.info('User chose to keep existing plan; exiting generation tool.')
        exit()

try:
    log.info('Starting population generation.')
    plans.generate(planspath, vehiclespath, modes, **conditions)
except:
    log.exception('Critical error while generating input plans; '
        'terminating process and exiting.')
    exit(1)

database.close()