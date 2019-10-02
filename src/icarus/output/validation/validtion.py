
import json
import sys
import os

from getpass import getpass
from argparse import ArgumentParser

if __name__ == '__main__':
    sys.path.insert(1, os.path.join(sys.path[0], '../..'))

from icarus.output.validation.database import ValidationDatabase
from icarus.util.print import Printer as pr

class OutputValidation:
    def __init__(self, database, encoding, config):
        self.database = ValidationDatabase(params=database, config=config)
        self.encoding = encoding

    def validate(self, fields, stats, silent=False):
        options = ('rmse', 'rmspe', 'me', 'mpe', 'correlation', 'coeff',
            'bias', 'variance', 'covariance')
        results = []
        results.append([' '] + [opt for opt in options if opt in stats])
        pr.print(f'Beginning MATSim output validation.', time=True)
        for tbl, col in fields:
            pr.print(f'Analyzing field "{col}" from table "{tbl}".')
            result = [f'{tbl} {col}']
            for opt in options:
                if opt in stats:
                    result.append(getattr(self.database, opt)(tbl, col))
            results.append(result)
        pr.print(f'MATSim output validation complete.', time=True)
        pr.print(pr.table(results, hrule=0, border=True))
                
                

if __name__ == '__main__':
    parser = ArgumentParser(prog='AgentsParser',
        description='Parses MATSim output into activites and routes in SQL.')
    parser.add_argument('--config', type=str,  dest='config',
        default=(os.path.dirname(os.path.abspath(__file__)) + '/config.json'),
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

        validator = OutputValidation(database, encoding, config)

        options = ('silent',)
        params = {key:config[key] for key in options if key in config}

        validator.validate(config['fields'], config['stats'], **params)

    except FileNotFoundError as err:
        print(f'Config file {args.config} not found.')
        quit()
    except json.JSONDecodeError as err:
        print(f'Config file {args.config} is not valid JSON.')
        quit()
    # except KeyError as err:
    #     print(f'Config file {args.config} is not valid config file.')
    #     quit()
    except Exception as err:
        raise(err)