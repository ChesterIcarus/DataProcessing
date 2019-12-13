
import csv

from icarus.abm.parse.agents.database import AgentsParserDatabase
from icarus.util.print import Printer as pr

class AgentsParser:
    def __init__(self, database, encoding):
        self.database = AgentsParserDatabase(database)
        self.encoding = encoding

    def parse(self, sourcepath, resume=False, silent=False, bin_size=100000):
        if not silent:
            pr.print(f'Beginning ABM agent data parsing from {sourcepath}',
                time=True)
            pr.print(f'Loading process metadata and resources.', time=True)

        target = sum(1 for l in open(sourcepath, 'r')) - 1
        agentsfile = open(sourcepath, 'r', newline='')
        parser = csv.reader(agentsfile, delimiter=',', quotechar='"')
        top = next(parser)
        cols = {key: val for key, val in zip(top, range(len(top)))}

        agents = []
        agent_id = 0

        if not silent:
            pr.print('Starting agents CSV file iteration.', time=True)
            pr.print('Agents Parsing Progress', persist=True, replace=True,
                frmt='bold', progress=agent_id/target)
        
        for agent in parser:
            agents.append((
                agent_id,
                int(agent[cols['hhid']]),
                int(agent[cols['pnum']]),
                float(agent[cols['pumsSerialNo']]),
                int(agent[cols['persType']]),
                int(agent[cols['persTypeDetailed']]),
                int(agent[cols['age']]),
                int(agent[cols['gender']]),
                int(agent[cols['industry']]),
                int(agent[cols['schlGrade']]),
                int(agent[cols['educLevel']]),
                int(agent[cols['workPlaceType']]),
                int(agent[cols['workPlaceTaz']]),
                int(agent[cols['workPlaceMaz']]),
                int(agent[cols['schoolType']]),
                int(agent[cols['schoolTaz']]),
                int(agent[cols['schoolMaz']]),
                int(agent[cols['campusBusinessTaz']]),
                int(agent[cols['campusBusinessMaz']]),
                int(agent[cols['dailyActivityPattern']])))
            agent_id += 1

            if agent_id % bin_size == 0:
                if not silent:
                    pr.print(f'Pushing {bin_size} agents to database.',
                        time=True)
                self.database.write_agents(agents)
                agents = []
                if not silent:
                    pr.print('Resuming agent CSV file parsing.', time=True)
                    pr.print('Agent Parsing Progress', persist=True,
                        replace=True, frmt='bold', progress=agent_id/target)

        if not silent:
            pr.print(f'Pushing {agent_id % bin_size} agents to database.',
                time=True)
        self.database.write_agents(agents)
        if not silent:
            pr.print('ABM agent data parsing complete.', time=True)
            pr.print('Agent Parsing Progress', persist=True, replace=True,
                frmt='bold', progress=1)
            pr.push()

    def create_idxs(self, silent=False):
        if not silent:
            pr.print(f'Creating all indexes in database {self.database.db}.', time=True)
        for tbl in self.database.tables:
            self.database.create_all_idxs(tbl)
        if not silent:
            pr.print(f'Index creating complete.', time=True)
                    
