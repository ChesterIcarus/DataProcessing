
import json

from getpass import getpass
from pkg_resources import resource_filename
from argparse import ArgumentParser

from icarus.util.print import PrintUtil as pr
from icarus.abm.parse.households.parser import HouseholdsParser

parser = ArgumentParser(prog='ABM Households Parser',
    description='Parse ABM households CSV file into table in a SQL database.')
parser.add_argument('--config', type=str,  dest='config',
    default=resource_filename('icarus', 'abm/parse/households/config.json'),
    help=('Specify a config file location; default is "config.json" in '
        'the current working directory.'))
parser.add_argument('--specs', type=str, dest='specs',
    default=resource_filename('icarus', 'abm/parse/households/specs.json'),
    help=('Specify a specs file location; default is "specs.json" in '
        'the current module directory.'))
parser.add_argument('--log', type=str, dest='log',
    help='specify a log file location; by default the log will not be saved',
    default=None)
args = parser.parse_args()

pr.print('Running ABM households parser module.', time=True)
pr.print('Validating configuration file.', time=True)
config = HouseholdsParser.validate_config(args.config, args.specs)

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

database['password'] = getpass(
    f'SQL password for {database["user"]}@localhost: ')

parser = HouseholdsParser(database)
parser.run(config)