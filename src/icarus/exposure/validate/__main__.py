
import logging

from getpass import getpass
from pkg_resources import resource_filename
from argparse import ArgumentParser

# command line argument processing
parser = ArgumentParser(prog='',
    description='')
parser.add_argument('--config', type=str,  dest='config',
    default=resource_filename('icarus', 'config.json'),
    help=('Specify a configuration file location; default is "config.json"'
        ' in the package module directory.'))
parser.add_argument('--specs', type=str, dest='specs',
    default=resource_filename('icarus', 'specs.json'),
    help=('Specify a specifications file location; default is "specs.json"'
        ' in the package module directory.'))
parser.add_argument('--log', type=str, dest='log', default=None,
    help='specify a log file location; by default the log will not be saved')
args = parser.parse_args()

# module loggging processing
logging.basicConfig(
    filename=args.log,
    filemode='w',
    format='%(asctime)s %(levelname)s %(filename)s:%(lineno)s   %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S:%03d',
    level=logging.INFO)

# configuration validation
logging.info('Validating module config with specs.')
config = {}
# config = [class].validate_config(args.config. args.specs)

# database credentials handling
database = config['database']
if database['user'] is None:
    database['user'] = input('SQL username for localhost: ')
if database['user'] is None or database['password'] is None:
    database['password'] = getpass('SQL password for '
        '{database["user"]}@localhost: ')

# module run
# module =
# module.run(config)