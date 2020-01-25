
import gzip
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
        planspath = config['run']['plans_file']
        bin_size = config['run']['bin_size']
        force = config['run']['force']

        act_types = tuple(config['encoding']['activity'].keys())
        leg_modes = ('bike', 'walk', 'car')

        log.info('Preallocating process files and tables.')
        self.create_tables('agents', 'activities', 'routes', force=force)

        log.info(f'Loading plans from {planspath}.')
        if planspath.split('.')[-1] == 'gz':
            plansfile = gzip.open(planspath, mode='rb')
        else:
            plansfile = open(planspath, mode='rb')

        parser = iterparse(plansfile, events=('start', 'end'))
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
        active = False
        transit = False

        start = None
        end = None
        prev_end = None

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
                        route_idx + act_idx,
                        None))
                    count += 1
                    route_idx = 0
                    act_idx = 0

                    if count == n:
                        log.info(f'Processed plan {count}.')
                        n <<= 1

                    if count % bin_size == 0:
                        log.debug('Pushing plans to mysql database.')
                        self.database.write_agents(agents)
                        self.database.write_activities(acts)
                        self.database.write_routes(routes)

                        agents = []
                        acts = []
                        routes = []
                        root.clear()

                elif elem.tag == 'activity':
                    act_type = elem.get('type')
                    if active:
                        if leg_mode in leg_modes:
                            start = self.parse_time(elem.get('dep_time'))
                            travel = self.parse_time(elem.get('trav_time'))
                            routes.append((
                                route_id,
                                agent_id,
                                route_idx,
                                start,
                                start + travel,
                                travel,
                                None))
                            route_id += 1
                            route_idx += 1
                        elif leg_mode in ('pt', 'non_network_walk'):
                            transit = True
                        else:
                            log.error(f'Found unexpected leg mode: "{leg_mode}".')
                            raise ValueError
                        active = False
                    if act_type in act_types:
                        prev_end = end
                        start = self.parse_time(elem.get('start_time', '04:00:00'))
                        end = self.parse_time(elem.get('end_time', '31:00:00'))
                        acts.append((
                            act_id,
                            agent_id,
                            act_idx,
                            start,
                            end,
                            end - start))
                        act_id += 1
                        act_idx += 1
                        if transit:
                            routes.append((
                                route_id,
                                agent_id,
                                route_idx,
                                prev_end,
                                start,
                                start - prev_end,
                                None))
                            route_id += 1
                            route_idx += 1
                            transit = False
                    elif act_type in ('pt interaction',):
                        transit = True
                    else:
                        log.error(f'Found unexpected activity type: "{act_type}".')
                        raise ValueError

                elif elem.tag == 'leg':
                    leg_mode = elem.get('mode')
                    active = True

        if count != (n >> 1):
            log.info(f'Processed plan {count}')
        
        if count % bin_size != 0:
            self.database.write_agents(agents)
            self.database.write_activities(acts)
            self.database.write_routes(routes)

        log.info('Closing plans file and completing parsing.')
        root.clear()
        plansfile.close()


    def create_tables(self, *tables, force=False):
        if not force:
            exists = self.database.table_exists(*tables)
            if len(exists):
                exists = '", "'.join(exists)
                log.warn(f'Table{"s" if len(exists) > 1 else ""} '
                    f'"{exists}" already exist in database '
                    f'"{self.database.db}". Drop and continue? [Y/n] ')
                if input().lower() not in ('y', 'yes'):
                    log.error('User chose to terminate process.')
                    raise RuntimeError
        for table in tables:
            self.database.create_table(table)


    def create_indexes(self, config):
        if config['run']['create_idxs']:
            log.info(f'Creating all indexes in database "{self.database.db}".')
            for tbl in self.database.tables:
                self.database.create_all_idxs(tbl)
            log.info(f'Index creation complete.')