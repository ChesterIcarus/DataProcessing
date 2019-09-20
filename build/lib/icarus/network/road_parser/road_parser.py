
import json
import os
import sys

from getpass import getpass
from argparse import ArgumentParser
from xml.etree.ElementTree import iterparse

if __name__ == '__main__':
    sys.path.insert(1, os.path.join(sys.path[0], '../..'))

from network.road_parser.road_parser_db import RoadParserDatabaseHandle
from  icarus.util.print import Printer as pr

class RoadParser:
    def __init__(self, database, encoding):
        self.database = RoadParserDatabaseHandle(database)
        self.encoding = encoding

    def parse_road(self, filepath, bin_size=1000000):
        pr.print(f'Beginning network road parsing from {filepath}.', time=True)

        parser = iterparse(filepath, events=('start', 'end'))
        parser = iter(parser)
        evt, root = next(parser)

        links = []
        nodes = []
        bin_count = 0

        for evt, elem in parser:
            if evt == 'start':
                if elem.tag == 'nodes':
                    pr.print('Starting road node parsing.', time=True)
                elif elem.tag == 'links':
                    pr.print('Starting road link parsing.', time=True)
            elif evt == 'end':
                if elem.tag == 'node':
                    nodes.append((
                        int(elem.get('id')),
                        f'POINT({elem.get("x")} {elem.get("y")})'))
                    bin_count += 1
                elif elem.tag == 'link':
                    links.append((
                        int(elem.get('id')),
                        int(elem.get('from')),
                        int(elem.get('to')),
                        float(elem.get('length')),
                        float(elem.get('freespeed')),
                        float(elem.get('capacity')),
                        float(elem.get('permlanes')),
                        bool(int(elem.get('oneway'))),
                        str(elem.get('modes'))))
                    bin_count += 1
                elif elem.tag == 'nodes':
                    pr.print(f'Pushing {len(nodes)} nodes to the database.', time=True)
                    self.database.write_nodes(nodes)
                    nodes = []
                    bin_count = 0
                    root.clear()
                elif elem.tag == 'links':
                    pr.print(f'Pushing {len(links)} links to the database.', time=True)
                    self.database.write_nodes(links)
                    links = []
                    bin_count = 0
                    root.clear()
                if bin_count == bin_size:
                    if len(nodes):
                        pr.print(f'Pushing {bin_count} nodes to the database.', time=True)
                        self.database.write_nodes(links)
                        links = []
                    elif len(links):
                        pr.print(f'Pushing {bin_count} links to the database.', time=True)
                        self.database.write_nodes(links)
                        links = []
                    bin_count = 0
                    root.clear()

        pr.print('Network road parsing complete.', time=True)

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
        encoding = params['encoding']
        database['password'] = getpass(
            f'SQL password for {database["user"]}@localhost: ')

        parser = RoadParser(database, encoding)

        if not params['resume']:
            for table in database['tables'].keys():
                parser.database.create_table(table)

        parser.parse_road(params['sourcepath'])

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