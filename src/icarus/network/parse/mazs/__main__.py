
import json

from getpass import getpass
from pkg_resources import resource_filename
from argparse import ArgumentParser

from icarus.network.parse.mazs.parser import MazParser
from icarus.util.print import Printer as pr


parser = ArgumentParser(prog='AgentsParser',
    description='Parse ABM agents csv file into table in a SQL database.')
parser.add_argument('--config', type=str,  dest='config',
    default=resource_filename('icarus', 'network/parse/mazs/config.json'),
    help=('Specify a config file location; default is "config.json" in '
        'the current working directory.'), nargs=1)
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

parser = MazParser(database)

if not config['resume']:
    for table in database['tables'].keys():
        parser.database.create_table(table)

parser.parse_mazs(config['sourcepath'])

if config['create_idxs']:
    pr.print('Beginning index creation on generated tables.', time=True)
    for table in database['tables']:
        parser.database.create_all_idxs(table)
    pr.print('Index creation complete.', time=True)