
import os
import logging as log
from argparse import ArgumentParser, SUPPRESS

from icarus.analyze.exposure.exposure import Exposure
from icarus.util.sqlite import SqliteUtil
from icarus.util.config import ConfigUtil

desc = (
    ''
)
parser = ArgumentParser('icarus.analyze.exposure', description=desc, add_help=False)

general = parser.add_argument_group('general options')
general.add_argument('--help', action='help', default=SUPPRESS,
    help='show this help menu and exit process')
general.add_argument('--dir', type=str, dest='dir', default='.',
    help='path to simulation data; default is current working directory')
general.add_argument('--log', type=str, dest='log', default=None,
    help='location to save additional logfiles')
general.add_argument('--level', type=str, dest='level', default='info',
    choices=('notset', 'debug', 'info', 'warning', 'error', 'critical'),
    help='level of verbosity to print log messages')
general.add_argument('--force', action='store_true', dest='force', 
    default=False, help='skip prompts for deleting files/tables')

configuration = parser.add_argument_group('configuration options')
configuration.add_argument('--source', type=str, dest='source', default='mrt',
    choices=('mrt', 'pet', 'utci', 'air'),
    help='temperature type to use in analysis')

args = parser.parse_args()

path = lambda x: os.path.abspath(os.path.join(args.dir, x))
os.makedirs(path('logs'), exist_ok=True)
homepath = path('')
logpath = path('logs/analyze_exposure.log')
dbpath = path('database.db')
configpath = path('config.json')

handlers = []
handlers.append(log.StreamHandler())
handlers.append(log.FileHandler(logpath))
if args.log is not None:
    handlers.append(log.FileHandler(args.log, 'w'))
if args.level == 'debug':
    frmt = '%(asctime)s %(levelname)s %(filename)s:%(lineno)s %(message)s'
else:
    frmt = '%(asctime)s %(levelname)s %(message)s'
log.basicConfig(
    format=frmt,
    level=getattr(log, args.level.upper()),
    handlers=handlers
)

log.info('Running abm parsing module.')
log.info(f'Loading data from {homepath}.')
log.info('Verifying process metadata/conditions.')

database = SqliteUtil(dbpath)
exposure = Exposure(database)

if not exposure.ready():
    log.error('Dependent data not parsed or generated; see warnings.')
    exit(1)
elif exposure.complete():
    log.warn('Exposure analysis already run. Would you like to run it again? [Y/n]')
    if input().lower() not in ('y', 'yes', 'yeet'):
        log.info('User chose to keep existing exposure analysis; exiting analysis tool.')
        exit()

try:
    log.info('Starting exposure analysis.')
    exposure.analyze(args.source)
except:
    log.exception('Critical error while analyzing exposure; '
        'terminating process and exiting.')
    exit(1)
