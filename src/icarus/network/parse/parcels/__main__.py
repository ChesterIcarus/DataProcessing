
import json

from getpass import getpass
from pkg_resources import resource_filename
from argparse import ArgumentParser

from icarus.network.parse.parcels.parser import ParcelsParser
from icarus.util.print import PrintUtil as pr


parser = ArgumentParser(prog='Network Parcel Parser',
    description='Parse Maricopa parcel data into SQL database.')
parser.add_argument('--config', type=str, dest='config',
    default=resource_filename('icarus', 'network/parse/parcels/config.json'),
    help=('Specify a config file location; default is "config.json" in '
        'the current working directory.'))
parser.add_argument('--specs', type=str, dest='specs',
    default=resource_filename('icarus', 'network/parse/parcels/specs.json'))
args = parser.parse_args()

pr.print('Running network parcel parser module.', time=True)
pr.print('Validating configuration file.', time=True)
config = ParcelsParser.validate_config(args.config, args.specs)

if args.log is not None:
    log = args.log
elif config['run']['log'] not in (None, ''):
    log = config['run']['log']
else:
    log = None
if log is not None:
    pr.log(log)
    pr.print(f'Process log being saved to {log}.', time=True)

database = config['database']
database['password'] = pr.getpass(f'SQL password for '
    f'{database["user"]}@localhost: ', time=True)

parser = ParcelsParser(database)
parser.run(config)
