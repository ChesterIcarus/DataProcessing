
import csv
import json
import os
import sys
from getpass import getpass

if __name__ == '__main__':
    sys.path.insert(1, os.path.join(sys.path[0], '../..'))

from abm.agents_parser.agents_parser_db import AgentsParserDatabaseHandle
from util.print_util import Printer as pr


class AgentsParser:
    def __init__(self, database, encoding):
        self.database = AgentsParserDatabaseHandle(database)
        self.encoding = encoding

    @staticmethod
    def decode_list(string):
        return [int(num) for num in string[1:-1].replace(' ', '').split(',')]

    def parse_agents(self, filepath, resume=False):
        pr.print(f'Beginning ABM agents parsing from {filepath}.', time=True)
        pr.print(f'Loading files and fetching reference data.', time=True)

        target = sum(1 for l in open(filepath, 'r')) - 1
        agentsfile = open(filepath, 'r', newline='')
        parser = csv.reader(agentsfile, delimiter=',', quotechar='"')
        top = next(parser)
        cols = {key: val for key, val in zip(top, range(len(top)))}

        agents = []
        agent_id = 0
        bin_size = 1000000

        if resume:
            pr.print('Identifying parsing resuming location.', time=True)
            offset = self.database.count_agents() - 1
            pr.print(f'Moving to resume location {offset}.', time=True)
            while agent_id < offset:
                next(parser)
                agent_id += 1

        pr.print('Resuming agent parsing.', time=True)
        pr.print('Agent Parsing Progress', persist=True, replace=True, 
            frmt='bold', progress=agent_id/target)

        for agent in parser:
            agents.append((
                agent_id,
                int(agent[cols['hhid']]),
                int(agent[cols['pnum']]),
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
        pr.print('Agent Parsing Progress', persist=True, replace=True, 
            frmt='bold', progress=1)
        pr.push()
        pr.print('ABM trip parsing complete.', time=True)
        agentsfile.close()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        configpath = sys.argv[1]
    else:
        configpath = os.path.dirname(os.path.abspath(__file__)) + '/config.json'
    try:
        with open(configpath) as handle:
            params = json.load(handle)['WORKSTATION']
        database = params['database']
        encoding = params['encoding']
        database['password'] = getpass(
            f'Password for {database["user"]}@localhost: ')
        parser = AgentsParser(database, encoding)
        if not params['resume']:
            for table in database['tables'].keys():
                parser.database.create_table(table)
        
        parser.parse_agents(params['sourcepath'], resume=params['resume'])
        
        if params['create_indexes']:
            pr.print('Beginning index creation on generated tables.', time=True)
            for tbl, table in database['tables'].items():
                for idx, index in table['indexes'].items():
                    pr.print(f'Creating index "{idx}" on table "{tbl}".', time=True)
                    parser.database.create_index(tbl, idx)
            pr.print('Index creation complete.', time=True)
    except FileNotFoundError as err:
        print(f'Config file {configpath} not found.')
        quit()
    except json.JSONDecodeError as err:
        print(f'Config file {configpath} is not valid JSON.')
        quit()
    except KeyError as err:
        print(f'Config file {configpath} is not valid config file.')
        quit()
    except Exception as err:
        raise(err)