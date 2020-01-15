
import logging as log

from collections import defaultdict
from xml.etree.ElementTree import iterparse

from icarus.exposure.analyze.link.database import ExposureLinkAnalysisDatabase
from icarus.util.config import ConfigUtil


class ExposureLinkAnalysis:
    def __init__(self, database):
        self.database = ExposureLinkAnalysisDatabase(database)


    @classmethod
    def validate_config(self, configpath, specspath):
        config = ConfigUtil.load_config(configpath)
        specs = ConfigUtil.load_specs(specspath)
        config = ConfigUtil.verify_config(specs, config)

        return config


    def run(self, config):
        log.info('Prallocating process files and tables.')
        force = config['run']['force']
        self.create_tables(*tuple(self.database.tables.keys()), force=force)

        eventsfile = config['run']['events_file']
        # input_db = config['run']['input_db']
        network_db = config['run']['network_db']
        default_temps = config['temperature']

        vehicles = defaultdict(lambda: [set(), None, 14400])
        agents = defaultdict(lambda: [list(), None, 14400, 0])

        acts = tuple(config['encoding']['activity'].keys())

        log.info('Fetching network and simulation data.')
        # log.info(f'Fetching population plans.')
        # plans = self.database.fetch_plans(input_db)
        log.info(f'Fetching network links.')
        links = self.database.fetch_links(network_db)
        log.info(f'Fetching network temperatures.')
        temps = self.database.fetch_temperatures(network_db)
        steps = len(temps[0])
        # log.info(f'Fetching network parcels.')
        # parcels = self.database.fetch_parcels(network_db)
        
        events = iter(iterparse(eventsfile, events=('start', 'end')))
        evt, root = next(events)
        count = 0
        time = 0
        n = 14400

        log.info('Iterating over events file.')
        for evt, elem in events:
            try:
                if evt == 'start' and elem.tag == 'event':
                    event = elem.get('type')
                    time = int(float(elem.get('time')))

                    if event == 'TransitDriverStarts':
                        agent_id = elem.get('driverId')
                        agent = agents[agent_id]
                        agent[0].append(0)
                        agent[2] = time

                    if event == 'entered link':
                        vehicle_id = elem.get('vehicle')
                        vehicle = vehicles[vehicle_id]
                        vehicle[2] = time

                    elif event == 'left link':
                        vehicle_id = elem.get('vehicle')
                        link_id = elem.get('link')
                        vehicle = vehicles[vehicle_id]
                        vehc_time = vehicle[2]
                        if vehicle[0]:
                            if vehicle_id[:3] == 'car':
                                temp = default_temps['car']
                            elif vehicle_id[:4] in ('walk', 'bike'):
                                step = int(time / 86400 * steps) % steps
                                temp = temps[links[link_id]][step]
                            elif vehicle_id[-3:] == 'bus':
                                temp = default_temps['bus']
                            elif vehicle_id[-4:] == 'tram':
                                temp = default_temps['tram']
                            else:
                                log.error(f'Unexpected vehicle with id {vehicle_id}.')
                                raise ValueError
                            exposure = temp * (time - vehc_time)
                            for agent_id in vehicle[0]:
                                agent = agents[agent_id]
                                agent[0][-1] += exposure
                        vehicle[2] = time

                    elif event == 'PersonEntersVehicle':
                        agent_id = elem.get('person')
                        vehicle_id = elem.get('vehicle')
                        vehicle = vehicles[vehicle_id]
                        vehicle[0].add(agent_id)

                    elif event == 'PersonLeavesVehicle':
                        agent_id = elem.get('person')
                        vehicle_id = elem.get('vehicle')
                        vehicle = vehicles[vehicle_id]
                        vehicle[0].remove(agent_id)

                    elif event == 'actend':
                        act = elem.get('actType')
                        if act in acts:
                            agent_id = elem.get('person')
                            link_id = elem.get('link')
                            agent = agents[agent_id]
                            agent[0].append(default_temps['room'] * (time - agent[2]))
                            agent[0].append(0)
                            agent[1] = link_id
                            agent[2] = time

                    elif event == 'actstart':
                        act = elem.get('actType')
                        if act in acts:
                            agent = elem.get('person')
                            link_id = elem.get('link')
                            agent = agents[agent_id]
                            agent[1] = link_id
                            agent[2] = time

                    elif event == 'stuckAndAbort':
                        agent_id = elem.get('person')
                        agent = agents[agent_id]
                        agent[3] = 1

                    count += 1
                    if time >= n:
                        log.info(f'Simulation analysis at {str(time//3600).zfill(2)}'
                            f':00:00 with {count} events processed.')
                        n += 3600
                    if count % 100000 == 0:
                        root.clear()

            except Exception:
                log.exception(f'Exception while handling event {count}.')
                exit()

        log.info('Simulation events iteration complete.')
        log.info('Processing and analyzing results.')

        activities = []
        routes = []
        plans = []
        end_time = time


        for agent_id, agent in agents.items():
            if agent_id.isdigit():
                for idx, exp in enumerate(agent[0]):
                    time = 14400
                    if idx % 2:
                        routes.append((agent_id, idx // 2, exp))
                    else:
                        activities.append((agent_id, idx // 2, exp))
                if agent[3] == 0 and len(agent[0]) % 2 == 0:
                    exp = default_temps['room'] * (end_time - agent[2])
                    activities.append((agent_id, len(agent[0]) // 2, exp))
                    size = len(agent[0]) + 1
                else:
                    size = len(agent[0])
                plans.append((agent_id, len(agent[0]), size, agent[3]))

        log.info(f'Saving results to database.')

        self.database.write_rows(plans, 'agents')
        self.database.write_rows(activities, 'activities')
        self.database.write_rows(routes, 'routes')

        if config['run']['create_idxs']:
            log.info(f'Creating all indexes in database '
                f'{self.database.db}.')
            self.create_idxs()
            log.info(f'Index creating complete.')


    def create_idxs(self):
        for tbl in self.database.tables:
            self.database.create_all_idxs(tbl)


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