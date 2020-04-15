
import logging as log
from enum import Enum


class VehicleMode(Enum):
    NONE = None
    BUS = 'bus'
    TRAM = 'tram'
    CAR = 'car'
    WALK = 'walk'


class RouterMode(Enum):
    NONE = None
    BUS = 'bus'
    BIKE = 'bike'
    CAR = 'car'
    NETWALK = 'netwalk'
    WALK = 'walk'
    PT = 'pt'

    @classmethod
    def parse(self, name):
        return getattr(self, name.upper())

    def transit(self):
        return self in (self.WALK, self.PT)


class Vehicle:
    @classmethod
    def get_mode(self, vehicle_id, error=True):
        mode = None
        if vehicle_id.isdigit():
            mode = VehicleMode.CAR
        if vehicle_id[:3] == VehicleMode.CAR.value:
            mode = VehicleMode.CAR
        elif vehicle_id[:4] == VehicleMode.WALK.value:
            mode = VehicleMode.WALK
        elif vehicle_id[-3:].lower() == VehicleMode.BUS.value:
            mode = VehicleMode.BUS
        elif vehicle_id[-4:].lower() == VehicleMode.TRAM.value:
            mode = VehicleMode.TRAM
        if error and mode is None:
            log.error(f'Unexpected vehicle with id {vehicle_id}.')
            raise ValueError
        return mode


    def __init__(self, vehicle_id, time, temperature=None):
        self.id = vehicle_id
        self.last_active = time
        self.temperature = temperature
        self.mode = self.get_mode(vehicle_id)
        self.agents = set()
        self.exposure = 0


    def move(self, time, temperature):
        if self.last_active is not None:
            temperature = self.temperature \
                if self.temperature is not None else temperature
            self.exposure += temperature * (time - self.last_active)
        self.last_active = time

        
    def add_agent(self, agent, time):
        self.move(time, 0)
        agent.expose(time, 0)
        agent.active_exposure -= self.exposure
        self.agents.add(agent)
    

    def remove_agent(self, agent, time):
        self.move(time, 0)
        agent.expose(time, 0)
        agent.active_exposure += self.exposure
        self.agents.remove(agent)


class VehicleDict:
    def __init__(self, default_temps):
        self.vehicles = {}
        self.temps = default_temps


    def vehicle_temperature(self, mode, error=False):
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
            vehicle = Vehicle(vehicle_id, None, None)
            vehicle.temp = self.vehicle_temperature(vehicle.mode)
            self.vehicles[vehicle_id] = vehicle
            return vehicle


    def __setitem__(self, vehicle_id, vehicle):
        self.vehicles[vehicle_id] = vehicle

    
    def __iter__(self):
        return iter(self.vehicles)


class ActivityType(Enum):
    NONE = None

    HOME = 0
    WORKPLACE = 1
    UNIVERSITY = 2
    SCHOOL = 3
    ESCORT = 4
    SCHOOL_ESCPORT = 41
    PURE_ESCORT = 411
    RIDESHARE_ESCORT = 412
    OTHER_ESCORT = 42
    SHOPPING = 5
    OTHER_MAINTENANCE = 6
    EATING_OUT = 7
    BREAKFAST = 71
    LUNCH = 72
    DINNER = 73
    VISITING = 8
    OTHER_DISCRETIONARY = 9
    SPECIAL_EVENT = 10
    WORK = 11
    WORK_BUSINESS = 12
    WORK_LUNCH = 13
    WORK_OTHER = 14
    WORK_RELATED = 15
    ASU_RELATED = 16

    PT_INTERACTION = 100

    @classmethod
    def parse(self, name):
        name = name.upper().replace(' ', '_')
        if name == 'ASU':
            name = 'ASU_RELATED'
        elif name == 'RIDESHARE':
            name = 'RIDESHARE_ESCORT'
        elif name == 'OTHER_MAINTENENCE':
            name = 'OTHER_MAINTENANCE'
        elif name == 'EATING':
            name = 'EATING_OUT'
        return getattr(self, name)


    def transit(self):
        return self == self.PT_INTERACTION


class Agent:
    def __init__(self, agent_id):
        self.id = agent_id
        self.activities = []
        self.routes = []

        self.active_transit = False
        self.active_type = ActivityType.NONE
        self.active_mode = RouterMode.NONE
        self.active_time = 14400
        self.active_exposure = 0

        self.recorded_time = 14400
        self.recorded_exposure = 0


    def expose(self, time, temperature):
        self.active_exposure += temperature * (time - self.active_time)
        self.active_time = time


    def record(self, time):
        self.recorded_exposure += self.active_exposure
        self.recorded_time = time
        self.active_exposure = 0


    def add_transit(self, time, temperature):
        self.expose(time, temperature)
        self.routes.append([
            'pt', 
            self.recorded_time, 
            time, 
            time - self.recorded_time, 
            self.active_exposure])
        self.record(time)
        self.active_transit = False


    def start_activity(self, activity, time, temperature):
        self.expose(time, temperature)

        if self.active_mode != RouterMode.NONE:
            name = self.active_mode.name.lower()
            log.error(f'Agent {self.id} tried to start activity "{activity}" '
                    f'while started route "{name}" has not ended yet.')
            raise ValueError

        if not activity.transit():
            if self.active_transit:
                self.add_transit(time, temperature)

        self.active_type = activity


    def end_activity(self, activity, time, temperature):
        self.expose(time, temperature)

        if self.active_type != activity:
            if len(self.activities):
                name = self.active_type.name.lower()
                log.error(f'Agent {self.id} tried to end activity "{activity}" '
                    f'while started activity "{name}" has not ended yet.')
                raise ValueError
            else:
                self.active_type = activity

        if not activity.transit():
            self.activities.append([
                activity.name.lower(), 
                self.recorded_time, 
                time, 
                time - self.recorded_time, 
                self.active_exposure])
            self.record(time)

        self.active_type = ActivityType.NONE


    def depart(self, mode, time, temperature):
        self.expose(time, temperature)
        if self.active_type != ActivityType.NONE:
            log.error('')
            raise ValueError

        if mode.transit():
            self.active_transit = True

        self.active_mode = mode


    def arrive(self, mode, time, temperature):
        self.expose(time, temperature)

        if self.active_mode != mode:
            log.error('')
            raise ValueError

        if not self.active_transit:
            self.routes.append([
                mode.name.lower(), 
                self.recorded_time, 
                time, 
                time - self.recorded_time, 
                self.active_exposure])
            self.record(time)

        self.active_mode = RouterMode.NONE


    def abort(self):
        if self.active_transit:
            self.routes.append([
                'pt', 
                self.recorded_time, 
                None, None, None])
        elif self.active_type != ActivityType.NONE:
            self.activities.append([
                self.active_type.name.lower(), 
                self.recorded_time, 
                None, None, None])
        elif self.active_mode != RouterMode.NONE:
            self.routes.append([
                self.active_mode.name.lower(),
                self.recorded_time,
                None, None, None])
    

    def dump_agent(self):
        return [
            self.id, 
            len(self.activities) + len(self.routes), 
            self.recorded_exposure ]
            

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

    
    def __iter__(self):
        return iter(self.agents)


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
        temperature = self.temps['room']
        for agent in self.agents.values():
            if agent.active_type == ActivityType.HOME:
                agent.end_activity(ActivityType.HOME, time, temperature)
            else:
                agent.abort()
