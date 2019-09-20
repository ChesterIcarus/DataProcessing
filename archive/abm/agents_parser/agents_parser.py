
import csv
import json
import os
import sys

from argparse import ArgumentParser
from getpass import getpass

if __name__ == '__main__':
    sys.path.insert(1, os.path.join(sys.path[0], '../..'))

from abm.agents_parser.agents_parser_db import AgentsParserDatabaseHandle
from  icarus.util.print import Printer as pr

class AgentsParser:
    def __init__(self, database, encoding):
        self.database = AgentsParserDatabaseHandle(database)
        self.encoding = encoding

    @staticmethod
    def decode_list(string):
        return [int(num) for num in string[1:-1].replace(' ', '').split(',')]

    def parse_agents(self, filepath, bin_size=1000000, resume=False):
        pr.print(f'Beginning ABM agents parsing from {filepath}.', time=True)
        pr.print(f'Loading process metadata and fetching reference data.', time=True)

        target = sum(1 for l in open(filepath, 'r')) - 1
        agentsfile = open(filepath, 'r', newline='')
        parser = csv.reader(agentsfile, delimiter=',', quotechar='"')
        top = next(parser)
        cols = {key: val for key, val in zip(top, range(len(top)))}

        agents = []
        agent_id = 0

        if resume:
            pr.print('Identifying parsing resuming location.', time=True)
            offset = self.database.count_agents() - 1
            pr.print(f'Moving to resume location {offset}.', time=True)
            while agent_id < offset:
                next(parser)
                agent_id += 1

        pr.print('Starting agent parsing.', time=True)
        pr.print('Agent Parsing Progress', persist=True, replace=True, 
            frmt='bold', progress=agent_id/target)

        for agent in parser:
            agents.append((
                agent_id,
                int(agent[cols['hhid']]),
                int(agent[cols['pnum']]) - 1,
                int(agent[cols['age']]),
                int(agent[cols['gender']]),
                int(agent[cols['persTypeDetailed']]),
                int(agent[cols['industry']]),
                int(agent[cols['educLevel']])))
            agent_id += 1

            if agent_id % bin_size == 0:
                pr.print(f'Pushing {bin_size} agents to the database.', time=True)
                self.database.push_agents(agents)
                pr.print('Agent Parsing Progress', persist=True, replace=True,
                    frmt='bold', progress=agent_id/target)
                pr.print(f'Resuming agent parsing.', time=True)
                agents = []

        pr.print(f'Pushing {agent_id % bin_size} agents to the database.', time=True)
        self.database.push_agents(agents)
        pr.print('Agent Parsing Progress', persist=True, replace=True, progress=1)
        pr.push()
        pr.print('ABM trip parsing complete.', time=True)
        agentsfile.close()

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

        parser = AgentsParser(database, encoding)

        if not params['resume']:
            for table in database['tables'].keys():
                parser.database.create_table(table)
        
        parser.parse_agents(params['sourcepath'], resume=params['resume'])
        
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