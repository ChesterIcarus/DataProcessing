
import logging

from getpass import getpass
from pkg_resources import resource_filename
from argparse import ArgumentParser

from icarus.exposure.analyze.link.analysis import ExposureLinkAnalysis

# command line argument processing

parser = ArgumentParser(prog='Simulation Exposure Analysis (Link Granularity)',
    description='')
parser.add_argument('--config', type=str,  dest='config',
    default=resource_filename('icarus', 'exposure/analyze/link/config.json'),
    help=('Specify a configuration file location; default is "config.json"'
        ' in the package module directory.'))
parser.add_argument('--specs', type=str, dest='specs',
    default=resource_filename('icarus', 'exposure/analyze/link/specs.json'),
    help=('Specify a specifications file location; default is "specs.json"'
        ' in the package module directory.'))
parser.add_argument('--log', type=str, dest='log',
    help='specify a log file location; by default the log will not be saved',)
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

logging.info('Running exposure link analysis module.')
logging.info('Validating configuration with module specifications.')
config = ExposureLinkAnalysis.validate_config(args.config, args.specs)

# database credentials handling

database = config['database']
if database['user'] in ('', None):
    logging.info('SQL username for localhost: ')
    database['user'] = input('')
if database['user'] in ('', None) or database['password'] in ('', None):
    logging.info(f'SQL password for {database["user"]}@localhost: ')
    database['password'] = getpass('')

try:
    module = ExposureLinkAnalysis(database)
    module.run(config)
except Exception:
    logging.exception('Fatal error while running module.')