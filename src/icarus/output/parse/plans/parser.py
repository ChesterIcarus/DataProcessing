
import logging as log
import numpy as np

from datetime import datetime
from xml.etree.ElementTree import iterparse

from icarus.output.parse.plans.database import PlansParserDatabase
from icarus.util.filesys import FilesysUtil
from icarus.util.config import ConfigUtil

class PlansParser:
    def __init__(self, database, encoding):
        self.database = PlansParserDatabase(database)
        self.encoding = encoding


    @staticmethod
    def parse_time( clk):
        clk = clk.split(':')
        return int(clk[0]) * 3600 + int(clk[1]) * 60 + int(clk[2])


    @classmethod
    def validate_config(self, configpath, specspath):
        config = ConfigUtil.load_config(configpath)
        specs = ConfigUtil.load_specs(specspath)
        config = ConfigUtil.verify_config(specs, config)

        return config
    

    def run(self, config):
        log.info('Preallocating process files and tables.')

        planspath = config['run']['plans_file']
        bin_size = config['run']['bin_size']

        if planspath.split('.')[-1] == '.gz':
            log.info('Decompressing outout plans.')
            planspath = FilesysUtil.decompress_gz(planspath)
            temp = True

        parser = iterparse(planspath, events=('start', 'end'))
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
        n = 1

        selected = False

        log.info(f'Iterating over plans file and parsing agent plans.')
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

                    if count == n:
                        log.info(f'Processed plan {count}.')
                        n <<= 1

                    if count % bin_size == 0:
                        self.database.write_agents(agents)
                        self.database.write_activities(acts)
                        self.database.write_routes(routes)

                        agents = []
                        acts = []
                        routes = []
                        root.clear()

                elif elem.tag == 'activity':
                    start = self.parse_time(elem.get('start_time', '04:00:00'))
                    end = self.parse_time(elem.get('end_time', '28:00:00'))
                    acts.append((
                        act_id,
                        agent_id,
                        act_idx,
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

        if count != (n >> 1):
            log.info(f'Processed plan {count}')
        
        self.database.write_agents(agents)
        self.database.write_activities(acts)
        self.database.write_routes(routes)

        root.clear()
        del parser

        if temp:
            FilesysUtil.delete_file(planspath)

        log.info('Output plans parsing complete.')


    def index(self):
        log.info(f'Creating all indexes in database "{self.database.db}".')
        for tbl in self.database.tables:
            self.database.create_all_idxs(tbl)
        log.info(f'Index creation complete.')