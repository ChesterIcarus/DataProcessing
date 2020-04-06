
import csv

from icarus.abm.parse.agents.database import AgentsParserDatabase
from icarus.util.print import PrintUtil as pr
from icarus.util.config import ConfigUtil

class AgentsParser:
    def __init__(self, database, encoding):
        self.database = AgentsParserDatabase(database)
        self.encoding = encoding


    @classmethod
    def validate_config(self, configpath, specspath):
        config = ConfigUtil.load_config(configpath)
        specs = ConfigUtil.load_specs(specspath)
        config = ConfigUtil.verify_config(specs, config)

        return config


    def parse(self, config):
        pr.print('Prallocating process files and tables.', time=True)
        force = config['run']['force']
        self.create_tables('agents', force=force)

        pr.print(f'Loading process metadata and resources.', time=True)
        agents_path = config['run']['agents_file']
        bin_size = config['run']['bin_size']

        target = sum(1 for l in open(agents_path, 'r')) - 1
        agentsfile = open(agents_path, 'r', newline='')
        parser = csv.reader(agentsfile, delimiter=',', quotechar='"')
        top = next(parser)
        cols = {key: val for key, val in zip(top, range(len(top)))}

        agents = []
        agent_id = 0

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
                pr.print(f'Pushing {bin_size} agents to database.', time=True)
                self.database.write_agents(agents)
                
                pr.print('Resuming agent CSV file parsing.', time=True)
                pr.print('Agent Parsing Progress', persist=True,
                    replace=True, frmt='bold', progress=agent_id/target)
                agents = []

        pr.print(f'Pushing {agent_id % bin_size} agents to database.', time=True)
        self.database.write_agents(agents)
        
        pr.print('Agent Parsing Progress', persist=True, replace=True,
            frmt='bold', progress=1)
        pr.push()
        pr.print('ABM agent data parsing complete.', time=True)

        if config['run']['create_idxs']:
            pr.print(f'Creating all indexes in database '
                f'{self.database.db}.', time=True)
            self.create_idxs()
            pr.print(f'Index creating complete.', time=True)


    def create_idxs(self, silent=False):
        for tbl in self.database.tables:
            self.database.create_all_idxs(tbl)


    def create_tables(self, *tables, force=False):
        if not force:
            exists = self.database.table_exists(tables)
            if len(exists):
                cond = pr.print(f'Tables "{exists}" already exist in database '
                    f'"{self.database.db}". Drop and continue? [Y/n] ', 
                    inquiry=True, time=True, force=True)
                if cond:
                    pr.print('User chose to terminate process.')
                    raise RuntimeError
        for table in tables:
            self.database.drop_table(table)
