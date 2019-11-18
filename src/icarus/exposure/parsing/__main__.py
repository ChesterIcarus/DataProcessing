
import json

from getpass import getpass
from pkg_resources import resource_filename
from argparse import ArgumentParser

from icarus.exposure.parsing.parser import DaymetParser

parser = ArgumentParser(prog='DaymetParser',
    description='Parses daymet tmerperature data into MySQL database.')
parser.add_argument('--config', type=str,  dest='config',
    default=resource_filename('icarus', 'exposure/parsing/config.json'),
    help=('Specify a config file location; default is "config.json" in '
        'the current working directory.'))
parser.add_argument('--log', type=str, dest='log',
    help='specify a log file location; by default the log will not be saved',
    default=None)
args = parser.parse_args()

if args.log is not None:
    pr.log(args.log)

try:
    with open(args.config) as handle:
        config = json.load(handle)
except FileNotFoundError as err:
    print(f'Config file {args.config} not found.')
except json.JSONDecodeError as err:
    print(f'Config file {args.config} is not valid JSON.')
except Exception as err:
    raise(err)

database = config['database']
database['password'] = getpass(f'SQL password for {database["user"]}@localhost: ')

parser = DaymetParser(database)
parser.run(config)