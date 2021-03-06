
import os
import logging as log
from argparse import ArgumentParser

from icarus.generate.config.config import Config
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

log.info('Running config generation tool.')
log.info(f'Loading run data from {home}.')

configurator = Config()

if not configurator.ready():
    log.error('Dependent data not parsed or generated; see warnings for details.')
    exit(1)
elif configurator.complete(args.folder):
    log.warning('Config already generated. Would you like to replace it? [Y/n]')
    if input().lower() not in ('y', 'yes', 'yeet'):
        log.info('User chose to keep existing config; exiting generation tool.')
        exit()

try:
    log.info('Starting config generation.')
    configurator.generate(args.folder, config)
except:
    log.exception('Critical error while generating config; '
        'terminating process and exiting.')
    exit(1)
