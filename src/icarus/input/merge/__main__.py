
import json

from getpass import getpass
from pkg_resources import resource_filename
from argparse import ArgumentParser

from icarus.input.merge.merger import PlansMerger
from icarus.util.print import Printer as pr

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

if args.log is not None:
    pr.log(args.log)

try:
    with open(args.config) as handle:
        config = json.load(handle)
except FileNotFoundError as err:
    pr.print(f'Config file {args.config} not found.', time=True)
    raise err
except json.JSONDecodeError as err:
    pr.print(f'Config file {args.config} is not valid JSON.', time=True)
    raise err
except KeyError as err:
    pr.print(f'Config file {args.config} is not valid config file.', time=True)
    raise err

database = config['database']

database['password'] = getpass(
    f'SQL password for {database["user"]}@localhost: ')

merger = PlansMerger(database)
merger.run(config)

