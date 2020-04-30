
import os
import logging as log
from argparse import ArgumentParser

from icarus.parse.roads.roads import Roads
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

networkpath = path('input/network.xml.gz')

log.info('Running roads parsing tool.')
log.info(f'Loading run data from {home}.')

database = SqliteUtil(path('database.db'))
roads = Roads(database)

if not roads.ready(networkpath):
    log.warning('Dependent data not parsed or generated.')
    log.warning('Roads parsing dependencies include network generation as well '
        'as exposure and regions parsing.')
    exit(1)
elif roads.complete():
    log.warning('Roads already parsed. Would you like to replace it? [Y/n]')
    if input().lower() not in ('y', 'yes', 'yeet'):
        log.info('User chose to keep existing roads; exiting parsing tool.')
        exit()

try:
    log.info('Starting roads parsing.')
    roads.parse(networkpath)
except:
    log.exception('Critical error while parsing roads; '
        'terminating process and exiting.')
    exit(1)


