
import json

from getpass import getpass
from pkg_resources import resource_filename
from argparse import ArgumentParser

from icarus.network.parcels_parser.parcels_parser import ParcelsParser
from icarus.util.print import Printer as pr


parser = ArgumentParser(prog='AgentsParser',
    description='Parse Maricopa parcel data into SQL database.')
parser.add_argument('--config', type=str,  dest='config',
    default=resource_filename('icarus', 'network/parcels_parser/config.json'),
    help=('Specify a config file location; default is "config.json" in '
        'the current working directory.'), nargs=1)
args = parser.parse_args()

try:
    with open(args.config) as handle:
        config = json.load(handle)

    database = config['database']
    
    database['password'] = getpass(
        f'SQL password for {database["user"]}@localhost: ')

    parser = ParcelsParser(database)
    
    parser.parse_parcels(config['shape_file'], config['residence_file'],
        config['commerce_file'])
    
    if config['create_idxs']:
        pr.print('Beginning index creation on generated tables.', time=True)
        for table in database['tables']:
            parser.database.create_all_idxs(table)
        pr.print('Index creation complete.', time=True)
    
except FileNotFoundError as err:
    print(f'Config file {args.config} not found.')
except json.JSONDecodeError as err:
    print(f'Config file {args.config} is not valid JSON.')
# except KeyError as err:
#     print(f'Config file {args.config} is not valid config file.')
except Exception as err:
    raise(err)