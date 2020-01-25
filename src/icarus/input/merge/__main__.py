
import json
import logging

from getpass import getpass
from pkg_resources import resource_filename
from argparse import ArgumentParser

from icarus.input.merge.merger import PlansMerger

# command line argument processing
parser = ArgumentParser(prog='PlansMerger',
    description='Merges output plans with vehicular data.')
parser.add_argument('--config', type=str,  dest='config',
    default=resource_filename('icarus', 'input/merge/config.json'),
    help=('Specify a config file location; default is "config.json" in '
        'the current working directory.'))
parser.add_argument('--log', type=str, dest='log',
    help='specify a log file location; by default the log will not be saved',
    default=None)
args = parser.parse_args()

# module loggging processing
handlers = []
handlers.append(logging.StreamHandler())
if args.log is not None:
    handlers.append(logging.FileHandler(args.log, 'w'))
logging.basicConfig(
    format='%(asctime)s %(levelname)s %(filename)s:%(lineno)s %(message)s',
    level=logging.DEBUG,
    handlers=handlers)

# config validation
logging.info('Running input plans merger module.')
logging.info('Validating configuration with module specifications.')
config = PlansMerger.validate_config(args.config)

# database credentials handling
database = config['database']
if database['user'] in ('', None):
    logging.info('SQL username for localhost: ')
    database['user'] = input('')
if database['user'] in ('', None) or database['password'] in ('', None):
    logging.info(f'SQL password for {database["user"]}@localhost: ')
    database['password'] = getpass('')

merger = PlansMerger(database)
merger.run(config)
