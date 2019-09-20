
import json

from getpass import getpass
from pkg_resources import resource_filename
from argparse import ArgumentParser

from icarus.network.road_parser.road_parser import RoadParser
from icarus.util.print import Printer as pr

parser = ArgumentParser(prog='AgentsParser',
    description='Parse ABM agents csv file into table in a SQL database.')
parser.add_argument('--config', type=str,  dest='config',
    default=resource_filename('icarus', 'network/road_parser/config.json'),
    help=('Specify a config file location; default is "config.json" in '
        'the current working directory.'), nargs=1)
args = parser.parse_args()

try:
    with open(args.config) as handle:
        config = json.load(handle)

    database = config['database']
    encoding = config['encoding']
    
    database['password'] = getpass(
        f'SQL password for {database["user"]}@localhost: ')

    parser = RoadParser(database, encoding)

    if not config['resume']:
        for table in database['tables'].keys():
            parser.database.create_table(table)

    parser.parse_road(config['sourcepath'])

    if config['create_idxs']:
        pr.print('Beginning index creation on generated tables.', time=True)
        for table in database['tables']:
            parser.database.create_all_idxs(table)
        pr.print('Index creation complete.', time=True)

except FileNotFoundError as err:
    print(f'Config file {args.config} not found.')
except json.JSONDecodeError as err:
    print(f'Config file {args.config} is not valid JSON.')
except KeyError as err:
    print(f'Config file {args.config} is not valid config file.')
except Exception as err:
    raise(err)