
import os
import gzip
import shutil

import numpy as np

from datetime import datetime
from xml.etree.ElementTree import iterparse

from icarus.output.plans_parser.database import PlansParserDatabase
from icarus.util.print import Printer as pr

class PlansParser:
    def __init__(self, database, encoding):
        self.database= PlansParserDatabase(database)
        self.encoding = encoding

    @staticmethod
    def decompress_plans(gzplans, plans):
        with open(plans, 'wb') as outfile, gzip.open(gzplans, 'rb') as infile:
            shutil.copyfileobj(infile, outfile)

    @staticmethod
    def parse_time( clk):
        clk = clk.split(':')
        return int(clk[0]) * 3600 + int(clk[1]) * 60 + int(clk[2])

    def parse(self, filepath, resume=False, bin_size=100000, silent=False):
        pr.print(f'Beginning MATSim output plans parsing from {filepath}.', time=True)
        pr.print('Loading process metadata and fetching reference data.', time=True)

        if not os.path.isfile(filepath):
            if os.path.isfile(filepath + '.gz'):
                self.decompress_plans(filepath + '.gz', filepath)
            else:
                raise FileNotFoundError

        # residences = self.database.get_residences()
        # commerces = self.database.get_commerces()
        
        parser = iterparse(filepath, events=('start', 'end'))
        parser = iter(parser)
        evt, root = next(parser)

        agents = []
        acts = []
        routes = []

        act_id = 0
        act_idx = 0
        route_id = 0
        route_idx = 0
        count = 0

        selected = False

        pr.print(f'Iterating over plans and parsing.', time=True)
        for evt, elem in parser:
            if evt == 'start':
                if elem.tag == 'person':
                    agent_id = int(elem.get('id'))
                if elem.tag == 'plan':
                    selected = True if elem.get('selected') == 'yes' else False
            elif evt == 'end' and selected:
                if elem.tag == 'plan':
                    agents.append((
                        agent_id,
                        route_idx + act_idx ))
                    count += 1
                    route_idx = 0
                    act_idx = 0

                    if count % bin_size == 0:
                        pr.print(f'Pushing {bin_size} plans to SQL server.', time=True)
                        self.database.write_agents(agents)
                        self.database.write_activities(acts)
                        self.database.write_routes(routes)

                        agents = []
                        acts = []
                        routes = []
                        root.clear()

                        pr.print('Resuming XML agent plan parsing.', time=True)
                elif elem.tag == 'activity':
                    # pt = f"POINT({elem.get('x')} {elem.get('y')})"
                    # apn = (residences[pt] if pt in residences else commerces[pt] 
                    #     if pt in commerces else None)
                    start = self.parse_time(elem.get('start_time', '00:00:00'))
                    end = self.parse_time(elem.get('end_time'))
                    acts.append((
                        act_id,
                        agent_id,
                        act_idx,
                        # apn, 
                        self.encoding['activity'][elem.get('type')],
                        start,
                        end,
                        end - start))
                    act_id += 1
                    act_idx += 1
                elif elem.tag == 'leg':
                    start = self.parse_time(elem.get('dep_time'))
                    travel = self.parse_time(elem.get('trav_time'))
                    routes.append((
                        route_id,
                        agent_id,
                        route_idx,
                        1,
                        start,
                        start + travel,
                        travel ))
                    route_id += 1
                    route_idx += 1

        pr.print(f'Pushing {count % bin_size} plans to SQL server.', time=True)
        self.database.write_agents(agents)
        self.database.write_activities(acts)
        self.database.write_routes(routes)

        root.clear()

        pr.print('Output plans parsing complete.', time=True)

    def index(self, silent=False):
        if not silent:
            pr.print(f'Creating all indexes in database "{self.database.db}"".',
                time=True)
        for tbl in self.database.tables:
            self.database.create_all_idxs(tbl)
        if not silent:
            pr.print(f'Index creating complete.', time=True)

    def verify(self, silent=False):
        pr.print(f'Beginning contradiction analysis.', time=True)
        
        pr.print(f'Contradiction analysis complete.', time=True)