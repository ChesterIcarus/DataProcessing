
import logging

from getpass import getpass
from pkg_resources import resource_filename
from argparse import ArgumentParser

from icarus.output.parse.plans.parser import PlansParser

# command line argument processing
parser = ArgumentParser(prog='Simulation Output Plans Parsing',
    description='Parse output plans from MATSim simulation into MySQL.')
parser.add_argument('--config', type=str,  dest='config',
    default=resource_filename('icarus', 'output/parse/plans/config.json'),
    help=('Specify a configuration file location; default is "config.json"'
        ' in the package module directory.'))
parser.add_argument('--specs', type=str, dest='specs',
    default=resource_filename('icarus', 'output/parse/plans/specs.json'),
    help=('Specify a specifications file location; default is "specs.json"'
        ' in the package module directory.'))
parser.add_argument('--log', type=str, dest='log',
    help='specify a log file location; by default the log will not be saved',)
args = parser.parse_args()

# module loggging processing
logging.basicConfig(
    format='%(asctime)s %(levelname)s %(filename)s:%(lineno)s %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(args.log, 'w'),
        logging.StreamHandler()
    ])

# config validation
logging.info('Running output plans parsing module module.')
logging.info('Validating configuration with module specifications.')
config = PlansParser.validate_config(args.config, args.specs)

# database credentials handling
database = config['database']
if database['user'] in ('', None):
    logging.debug('SQL username for localhost: ')
    database['user'] = input()
if database['user'] in ('', None) or database['password'] in ('', None):
    logging.debug(f'SQL password for {database["user"]}@localhost: ')
    database['password'] = getpass()

module = PlansParser(database, config['encoding'])
module.run(config)