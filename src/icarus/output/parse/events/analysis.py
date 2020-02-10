
import csv
import gzip
import logging as log

from collections import defaultdict
from xml.etree.ElementTree import iterparse

from icarus.output.parse.events.database import ExposureLinkAnalysisDatabase
from icarus.util.config import ConfigUtil


class Vehicle:
    BUS = 'bus'
    TRAM = 'tram'
    CAR = 'car'
    WALK = 'walk'

    @classmethod
    def get_mode(self, vehicle_id, error=True):
        mode = None
        if vehicle_id[:3] == self.CAR:
            mode = self.CAR
        elif vehicle_id[:4] == self.WALK:
            mode = self.WALK
        elif vehicle_id[-3:] == self.BUS:
            mode = self.BUS
        elif vehicle_id[-4:] == self.TRAM:
            mode = self.TRAM
        if error and mode is None:
            log.error(f'Unexpected vehicle with id {vehicle_id}.')
            raise ValueError
        return mode


    def __init__(self, vehicle_id, time, temp=None):
        self.agents = set()
        self.id = vehicle_id
        self.time = time
        self.temp = temp
        self.mode = self.get_mode(vehicle_id)
        self.exposure = 0


    def move(self, time, temp):
        temp = self.temp if self.temp is not None else temp
        self.exposure += temp * (time - self.time)

        
    def add_agent(self, agent, time):
        agent.exposure -= self.exposure
        agent.active_time = time
        self.agents.add(agent)


    def remove_agent(self, agent, time):
        agent.exposure += self.exposure
        agent.active_time = time
        self.agents.remove(agent)
    


class VehicleDict:
    def __init__(self, default_temps):
        self.vehicles = {}
        self.temps = default_temps


    def vehicle_temp(self, mode, error=False):
        temp = None
        if mode in self.temps:
            return self.temps[mode]
        if error and temp is None:
            log.error(f'Vehicle mode {mode} expected to have default '
                'temperature value but none was given.')
            raise ValueError
        return temp


    def __getitem__(self, vehicle_id):
        if vehicle_id in self.vehicles:
            return self.vehicles[vehicle_id]
        else:
            vehicle = Vehicle(vehicle_id, 14400, None)
            vehicle.temp = self.vehicle_temp(vehicle.mode)
            self.vehicles[vehicle_id] = vehicle
            return vehicle


    def __setitem__(self, vehicle_id, vehicle):
        self.vehicles[vehicle_id] = vehicle



class Agent:
    NONE = None
    NET_ACT = 0
    NET_LEG = 1
    PT_ACT = 2
    PT_LEG = 3

    modes: tuple
    acts: tuple
    vehicles: VehicleDict

    @classmethod
    def configure_agents(self, modes, activity_types, vehicles):
        self.modes = modes
        self.acts = activity_types
        self.vehicles = vehicles


    def __init__(self, agent_id):
        self.id = agent_id
        self.activities = []
        self.routes = []

        self.exposure = 0
        self.total_exposure = 0
        
        self.active_time = 14400
        self.record_time = 14400

        self.active = self.NONE
        self.last_mode = None
        self.last_act = None


    def start_activity(self, act, time, temp):
        if act in self.acts:
            if self.active == self.PT_LEG:
                self.arrive('pt', self.active_time, 0)
            self.active = self.NET_ACT
            self.record_time = time
        else:
            self.active = self.PT_ACT
        
        self.exposure += (time - self.active_time) * temp
        self.active_time = time
        self.last_act = act


    def end_activity(self, act, time, temp):
        self.exposure+= (time - self.active_time) * temp
        self.active_time = time
        self.active = self.NONE

        if act in self.acts:
            self.activities.append([act, self.record_time, time, time - self.record_time, self.exposure])
            self.total_exposure += self.exposure
            self.record_time = time
            self.exposure = 0


    def depart(self, mode, time, temp):
        if mode in self.modes:
            self.active = self.NET_LEG
        else:
            self.active = self.PT_LEG
        
        self.exposure += (time - self.active_time) * temp
        self.active_time = time
        self.last_mode = mode         


    def arrive(self, mode, time, temp):
        self.exposure += (time - self.active_time) * temp
        self.active_time = time
        self.active = self.NONE

        if mode in self.modes:
            self.routes.append([mode, self.record_time, time, time - self.record_time, self.exposure])
            self.total_exposure += self.exposure
            self.exposure = 0


    def abort(self):
        if self.active == self.NET_ACT:
            self.activities.append([self.last_act, self.record_time, None, None, None])
        elif self.active == self.PT_ACT or self.active == self.PT_LEG:
            self.routes.append(['pt', self.record_time, None, None, None])
        elif self.active == self.NET_LEG:
            self.routes.append([self.last_mode, self.record_time, None, None, None])
    

    def dump_agent(self):
        return [
            self.id, 
            len(self.activities) + len(self.routes), 
            self.total_exposure ]
            

    def dump_activities(self):
        activities = []
        size = len(self.activities)
        for idx, activity in zip(range(size), self.activities):
            activities.append([self.id, idx] + activity)

        return activities


    def dump_routes(self):
        routes = []
        size = len(self.routes)
        for idx, route in zip(range(size), self.routes):
            routes.append([self.id, idx] + route)

        return routes


class AgentDict:
    count = 0
    n = 1

    def __init__(self, defualt_temps):
        self.agents = {}
        self.temps = defualt_temps


    def __getitem__(self, agent_id):
        if agent_id in self.agents:
            return self.agents[agent_id]
        else:
            agent = Agent(agent_id)
            self.agents[agent_id] = agent
            return agent


    def __setitem__(self, agent_id, event):
        self.agents[agent_id] = event


    def dump_plans(self, size, delete=True):
        agent_ids = tuple(self.agents.keys())[:size]
        activities = []
        routes = []
        agents = []
        for agent_id in agent_ids:
            agent = self.agents[agent_id]
            activities.extend(agent.dump_activities())
            routes.extend(agent.dump_routes())
            agents.append(agent.dump_agent())
            if delete:
                del self.agents[agent_id]
            self.count += 1
            if self.count == self.n:
                log.info(f'Dumped agent {self.count}.')
                self.n <<= 1

        if not self.size() and self.count != (self.n << 1):
            log.info(f'Dumped agent {self.count}.')
            self.count = 0
            self.n = 1

        return activities, agents, routes


    def size(self):
        return len(self.agents)


    def filter_agents(self, condition):
        remove = []
        for agent in self.agents.values():
            if condition(agent):
                remove.append(agent.id)
        for agent_id in remove:
            del self.agents[agent_id]


    def close_activities(self, time):
        temp = self.temps['room']
        for agent in self.agents.values():
            if agent.active == Agent.NET_ACT and agent.last_act == 'home':
                agent.end_activity('home', time, temp)
            else:
                agent.abort()
        


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
        force = config['run']['force']
        eventspath = config['run']['events_file']
        network_db = config['run']['network_db']
        defualt_temps = config['temperature']
        acts = tuple(config['encoding']['activity'].keys())
        modes = ('netwalk', 'bike', 'car')

        vehicles = VehicleDict(defualt_temps)
        agents = AgentDict(defualt_temps)

        Agent.configure_agents(modes, acts, vehicles)

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

        log.info('Iterating over events file.')
        for evt, elem in events:
            if evt == 'end' and elem.tag == 'event':
                event = elem.get('type')
                time = int(float(elem.get('time')))

                if event == 'TransitDriverStarts':
                    agent = agents[elem.get('driverId')]

                if event == 'entered link':
                    pass
                    
                elif event == 'left link':
                    link = links[elem.get('link')]
                    vehicle = vehicles[elem.get('vehicle')]
                    temp = get_temp(link, time) if vehicle.temp is None else vehicle.temp
                    vehicle.move(time, temp)

                elif event == 'PersonEntersVehicle':
                    agent = agents[elem.get('person')]
                    vehicle = vehicles[elem.get('vehicle')]
                    vehicle.add_agent(agent, time)

                elif event == 'PersonLeavesVehicle':
                    agent = agents[elem.get('person')]
                    vehicle = vehicles[elem.get('vehicle')]
                    vehicle.remove_agent(agent, time)

                elif event == 'actend':
                    act = elem.get('actType')
                    agent = agents[elem.get('person')]
                    link = links[elem.get('link')]
                    temp = get_temp(link, time)
                    agent.end_activity(act, time, temp)

                elif event == 'actstart':
                    act = elem.get('actType')
                    agent = agents[elem.get('person')]
                    link = links[elem.get('link')]
                    # temp = get_temp(link, time)
                    temp = defualt_temps['room']    
                    agent.start_activity(act, time, temp)

                elif event == 'departure':
                    agent = agents[elem.get('person')]
                    mode = elem.get('legMode')
                    link = links[elem.get('link')]
                    temp = get_temp(link, time)
                    agent.depart(mode, time, temp)
                
                elif event == 'arrival':
                    agent = agents[elem.get('person')]
                    mode = elem.get('legMode')
                    link = links[elem.get('link')]
                    temp = get_temp(link, time)
                    agent.arrive(mode, time, temp)

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

        agents.filter_agents(lambda agent: not agent.id.isdigit())
        agents.close_activities(time)

        log.info(f'Dumping results to activity, agent, and route csv files.')

        activity_file = open(config['csv']['activities'], 'w')
        agent_file = open(config['csv']['agents'], 'w')
        route_file = open(config['csv']['routes'], 'w')

        activity_writer = csv.writer(activity_file)
        agent_writer = csv.writer(agent_file)
        route_writer = csv.writer(route_file)

        activity_writer.writerow(('agent_id', 'agent_idx', 'type', 'start', 'end', 'duration', 'exposure'))
        agent_writer.writerow(('agent_id', 'size', 'exposure'))
        route_writer.writerow(('agent_id', 'agent_idx', 'mode', 'start', 'end', 'duration', 'exposure'))

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
