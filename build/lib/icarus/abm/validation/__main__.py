
import json

from getpass import getpass
from pkg_resources import resource_filename
from argparse import ArgumentParser

from icarus.util.print import Printer as pr

if __name__ == '__main__':
    parser = ArgumentParser(prog='AgentsParser',
        description='Validation and visualizationtool for the ABM data.')
    parser.add_argument('--config', type=str,  dest='config',
        default=resource_filename('icarus', 'abm/validation/config.json'),
        help=('Specify a config file location; default is "config.json" in '
            'the current working directory.'))
    parser.add_argument('--log', type=str, dest='log',
        help='specify a log file location; by default the log will not be saved',
        default=None)
    args = parser.parse_args()

    try:
        if args.log is not None:
            pr.log(args.log)
        
        with open(args.config) as handle:
            config = json.load(handle)

        database = config['database']
        encoding = config['encoding']

        database['password'] = getpass(
            f'SQL password for {database["user"]}@localhost: ')

        validator = AbmValidation(database)
        validator.validate(config['charts'])


    except FileNotFoundError as err:
        print(f'Config file {args.config} not found.')
    except json.JSONDecodeError as err:
        print(f'Config file {args.config} is not valid JSON.')
    except KeyError as err:
        print(f'Config file {args.config} is not valid config file.')
    except Exception as err:
        raise(err)