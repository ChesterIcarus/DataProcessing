
import json
import os
import sys
import shapefile

from getpass import getpass
from argparse import ArgumentParser
from xml.etree.ElementTree import iterparse

if __name__ == '__main__':
    sys.path.insert(1, os.path.join(sys.path[0], '../..'))

from network.maz_parser.maz_parser_db import MazParserDatabaseHandle
from  icarus.util.print import Printer as pr

class MazParser:
    def __init__(self, database):
        self.database = MazParserDatabaseHandle(database)

    @staticmethod        
    def encode_poly(poly):
        return 'POLYGON((' + ','.join(str(pt[0]) + ' ' +
                str(pt[1]) for pt in poly) + '))'

    def parse_mazs(self, filepath, bin_size=10000):
        pr.print(f'Beginning network MAZ parsing from {filepath}.', time=True)
        pr.print('MAZ Parsing Progress', persist=True, replace=True,
            frmt='bold', progress=0)

        parser = shapefile.Reader(filepath)
        target = len(parser)
        mazs = []
        count = 0
        
        for item in parser:
            if item.record.County == 'MC':
                mazs.append((
                    item.record.MAZ_ID_10,
                    item.record.TAZ_2015,
                    item.record.Sq_miles,
                    self.encode_poly(item.shape.points)))
                count += 1
            if count % bin_size == 0:
                pr.print(f'Pushing {bin_size} MAZs to database.', time=True)
                self.database.push_mazs(mazs)
                mazs = []
                pr.print('Resuming MAZ parsing.', time=True)
                pr.print('MAZ Parsing Progress', persist=True, replace=True,
                    frmt='bold', progress=count/target)

        pr.print(f'Pushing {count % bin_size} MAZs to database.', time=True)
        self.database.push_mazs(mazs)
        pr.print('MAZ Parsing Progress', persist=True, replace=True,
            frmt='bold', progress=1)
        pr.push()
        pr.print('Network MAZ parsing complete.', time=True)

if __name__ == '__main__':
    cmdline = ArgumentParser(prog='AgentsParser',
        description='Parse ABM agents csv file into table in a SQL database.')
    cmdline.add_argument('--config', type=str,  dest='config',
        default=(os.path.dirname(os.path.abspath(__file__)) + '/config.json'),
        help=('Specify a config file location; default is "config.json" in '
            'the current working directory.'), nargs=1)
    args = cmdline.parse_args()

    try:
        with open(args.config) as handle:
            params = json.load(handle)['WORKSTATION']
        database = params['database']
        database['password'] = getpass(
            f'SQL password for {database["user"]}@localhost: ')

        parser = MazParser(database)

        if not params['resume']:
            for table in database['tables'].keys():
                parser.database.create_table(table)

        parser.parse_mazs(params['filepath'])
        
        if params['create_indexes']:
            pr.print('Beginning index creation on generated tables.', time=True)
            for table in database['tables']:
                parser.database.create_all_idxs(table)
            pr.print('Index creation complete.', time=True)

    except FileNotFoundError as err:
        print(f'Config file {args.config} not found.')
        quit()
    except json.JSONDecodeError as err:
        print(f'Config file {args.config} is not valid JSON.')
        quit()
    except KeyError as err:
        print(f'Config file {args.config} is not valid config file.')
        quit()
    except Exception as err:
        raise(err)