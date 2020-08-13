
import os
import logging as log
from argparse import ArgumentParser, SUPPRESS

from icarus.generate.network.network import Network
from icarus.util.config import ConfigUtil
from icarus.util.sqlite import SqliteUtil

desc = (
    'Generate the simulation network by parsing and merging the '
    'openstreetmap network feature data and the city tranist GTRFS '
    'data. This module creates temporary configuration files and uses '
    'osmosis and pt2matsim to generate the final network.'
)
parser = ArgumentParser('icarus.generate.network', 
    description=desc, add_help=False)

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

args = parser.parse_args()

path = lambda x: os.path.abspath(os.path.join(args.dir, x))
os.makedirs(path('logs'), exist_ok=True)
homepath = path('')
logpath = path('logs/parse_network.log')
configpath = path('config.json')

handlers = []
handlers.append(log.StreamHandler())
handlers.append(log.FileHandler(logpath))
if args.log is not None:
    handlers.append(log.FileHandler(args.log, 'w'))
log.basicConfig(
    format='%(asctime)s %(levelname)s %(filename)s:%(lineno)s %(message)s',
    level=getattr(log, args.level.upper()),
    handlers=handlers
)

log.info('Running network generation module.')
log.info(f'Loading data from {homepath}.')
log.info('Verifying process metadata/conditions.')


config = ConfigUtil.load_config(configpath)
networkpath = config['network']

network = Network()

if not network.ready(networkpath):
    log.error('Process dependencies not met; see warnings and '
        'documentation for more details.')
    exit(1)
elif network.complete(homepath) and not args.force:
    log.error('Some or all of this process is already complete.')
    log.error('Would you like to continue? [Y/n]')
    if input().lower() not in ('y', 'yes', 'yeet'):
        exit()

try:
    log.info('Starting network generation.')
    network.generate(args.dir, networkpath, config['resources'])
except:
    log.exception('Critical error while generating network; '
        'terminating process and exiting.')
    exit(1)
