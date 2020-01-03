
import json

from getpass import getpass
from pkg_resources import resource_filename
from argparse import ArgumentParser

from icarus.input.configure.configurator import Configurator
from icarus.util.print import PrintUtil as pr


parser = ArgumentParser(prog='MATSim Configurator',
    description='Build a configuration file for a MatSim simulation.')
parser.add_argument('--config', type=str,  dest='config',
    default=resource_filename('icarus', 'input/config/config.json'),
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

configurator = Configurator(config)
configurator.build_config()
