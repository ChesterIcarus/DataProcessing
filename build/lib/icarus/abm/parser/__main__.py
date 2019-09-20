
import json

from getpass import getpass
from pkg_resources import resource_filename
from argparse import ArgumentParser

from icarus.util.print import Printer as pr
from icarus.abm.parser.parser import AbmParser

if __name__ == '__main__':    

    parser = ArgumentParser(prog='AgentsParser',
        description='Parse ABM trips CSV file into table in a SQL database.')
    parser.add_argument('--config', type=str,  dest='config',
        default=resource_filename('icarus', 'abm/parser/config.json'),
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

        parser = AbmParser(database, encoding)

        if not config['resume']:
            for table in database['tables'].keys():
                parser.database.create_table(table)

        options = ('silent', 'bin_size', 'resume')
        params = {key:config[key] for key in options if key in config}

        parser.parse(config['sourcepath'], **params)

        if config['create_idxs']:
            parser.create_idxs()

    except FileNotFoundError as err:
        print(f'Config file {args.config} not found.')
    except json.JSONDecodeError as err:
        print(f'Config file {args.config} is not valid JSON.')
    except KeyError as err:
        print(f'Config file {args.config} is not valid config file.')
    except Exception as err:
        raise(err)