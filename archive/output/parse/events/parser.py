
import csv
import gzip
import logging as log

from collections import defaultdict
from xml.etree.ElementTree import iterparse, tostring

from icarus.output.parse.events.database import OutputEventsParserDatabaseUtil
from icarus.objects.simulation import *
from icarus.util.config import ConfigUtil


class OutputEventsParser:
    def __init__(self, database):
        self.database = OutputEventsParserDatabaseUtil(database)
        

    @classmethod
    def validate_config(self, configpath, specspath):
        config = ConfigUtil.load_config(configpath)
        specs = ConfigUtil.load_specs(specspath)
        config = ConfigUtil.verify_config(specs, config)

        return config


    def run(self, config):
        force = config['run']['force']
        eventspath = config['run']['events_file']
        network_db = config['run']['network_db']
        defualt_temps = config['temperature']

        vehicles = VehicleDict(defualt_temps)
        agents = AgentDict(defualt_temps)

        log.info('Preallocating process files and tables.')
        self.create_tables(*tuple(self.database.tables.keys()), force=force)

        log.info(f'Fetching network links.')
        links = self.database.fetch_links(network_db)

        log.info(f'Fetching network temperatures.')
        temps = self.database.fetch_temperatures(network_db)
        steps = len(temps[0])

        get_temp = lambda link, time: \
            temps[link][int(time / 86400 * steps) % steps]

        log.info(f'Loading events from {eventspath}.')
        if eventspath.split('.')[-1] == 'gz':
            eventsfile = gzip.open(eventspath, mode='rb')
        else:
            eventsfile = open(eventspath, mode='rb')
        
        events = iter(iterparse(eventsfile, events=('start', 'end')))
        evt, root = next(events)
        count = 0
        time = 0
        n = 14400

        debug = '2475627'

        log.info('Iterating over events file.')
        for evt, elem in events:
            if evt == 'end' and elem.tag == 'event':
                event = elem.get('type')
                time = int(float(elem.get('time')))

                if event == 'TransitDriverStarts':
                    agent = agents[elem.get('driverId')]

                elif event == 'left link':
                    pass
                    
                elif event == 'entered link':
                    link = links[elem.get('link')]
                    vehicle = vehicles[elem.get('vehicle')]
                    temperature = get_temp(link, time) \
                        if vehicle.temperature is None else vehicle.temperature
                    vehicle.move(time, temperature)

                elif event == 'PersonEntersVehicle':
                    agent = agents[elem.get('person')]
                    vehicle = vehicles[elem.get('vehicle')]
                    vehicle.add_agent(agent, time)

                    if agent.id == debug:
                        log.info(f'{time}: person entered vehicle')
                        log.info(f'{time}: {agent.active_exposure}')
                        log.info(f'{time}: {agent.recorded_exposure}')

                elif event == 'PersonLeavesVehicle':
                    agent = agents[elem.get('person')]
                    vehicle = vehicles[elem.get('vehicle')]

                    vehicle.remove_agent(agent, time)

                    if vehicle.id == debug:
                        log.info(f'{time}: person exited vehicle')
                        log.info(f'{time}: {agent.active_exposure}')
                        log.info(f'{time}: {agent.recorded_exposure}')
                    
                elif event == 'actend':
                    act = ActivityType.parse(elem.get('actType'))
                    agent = agents[elem.get('person')]
                    temperature = defualt_temps['room']
                    agent.end_activity(act, time, temperature)

                    if agent.id == debug:
                        log.info(f'{time}: person leaves activity')
                        log.info(f'{time}: {agent.active_exposure}')
                        log.info(f'{time}: {agent.recorded_exposure}')

                elif event == 'actstart':
                    act = ActivityType.parse(elem.get('actType'))
                    agent = agents[elem.get('person')]
                    link = links[elem.get('link')]
                    temperature = get_temp(link, time)
                    agent.start_activity(act, time, temperature)

                    if agent.id == debug:
                        log.info(f'{time}: person start activity')
                        log.info(f'{time}: {agent.active_exposure}')
                        log.info(f'{time}: {agent.recorded_exposure}')
                    
                elif event == 'departure':
                    agent = agents[elem.get('person')]
                    mode = RouterMode.parse(elem.get('legMode'))
                    link = links[elem.get('link')]
                    temperature = get_temp(link, time)
                    agent.depart(mode, time, temperature)

                    if agent.id == debug:
                        log.info(f'{time}: person departs')
                        log.info(f'{time}: {agent.active_exposure}')
                        log.info(f'{time}: {agent.recorded_exposure}')
                
                elif event == 'arrival':
                    agent = agents[elem.get('person')]
                    mode = RouterMode.parse(elem.get('legMode'))
                    link = links[elem.get('link')]
                    temperature = get_temp(link, time)
                    agent.arrive(mode, time, temperature)

                    if agent.id == debug:
                        log.info(f'{time}: person arrives')
                        log.info(f'{time}: {agent.active_exposure}')
                        log.info(f'{time}: {agent.recorded_exposure}')

                elif event == 'stuckAndAbort':
                    pass

                count += 1
                if time >= n:
                    log.info(f'Simulation analysis at {str(time//3600).zfill(2)}'
                        f':00:00 with {count} events processed.')
                    n += 3600
                if count % 100000 == 0:
                    root.clear()

        log.info('Closing events file and completing parsing.')
        root.clear()
        eventsfile.close()

        log.info('Processing and analyzing results.')

        agents.filter_agents(lambda agent: (not agent.id.isdigit()))
        agents.close_activities(time)

        log.info(f'Dumping results to activity, agent, and route csv files.')

        activity_file = open(config['csv']['activities'], 'w')
        agent_file = open(config['csv']['agents'], 'w')
        route_file = open(config['csv']['routes'], 'w')

        activity_writer = csv.writer(activity_file)
        agent_writer = csv.writer(agent_file)
        route_writer = csv.writer(route_file)

        agent_writer.writerow(('agent_id', 'size', 'exposure'))
        activity_writer.writerow(('agent_id', 'agent_idx', 'type', 'start',
            'end', 'duration', 'exposure'))
        route_writer.writerow(('agent_id', 'agent_idx', 'mode', 'start', 
            'end', 'duration', 'exposure'))

        while agents.size():
            plans = agents.dump_plans(100000)
            activity_writer.writerows(plans[0])
            agent_writer.writerows(plans[1])
            route_writer.writerows(plans[2])
        
        activity_file.close()
        agent_file.close()
        route_file.close()

        del plans
        del agents
        del vehicles

        log.info(f'Saving results to database.')

        self.database.load_activities(config['csv']['activities'])
        self.database.load_routes(config['csv']['routes'])
        self.database.load_agents(config['csv']['agents'])
        

    def create_idxs(self, config):
        if config['run']['create_idxs']:
            log.info(f'Creating all indexes in database {self.database.db}.')
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
