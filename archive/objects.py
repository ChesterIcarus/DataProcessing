
import logging as log

from random import randint
from enum import IntEnum, Enum

from icarus.util.general import defaultdict


class ActivityType(IntEnum):
    HOME = 0
    WORKPLACE = 1
    UNIVERSITY = 2
    SCHOOL = 3
    ESCORT = 4
    SCHOOL_ESCPORT = 41
    PURE_ESCROT = 411
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
    ASU = 16

    def escort(self):
        return self in (
            self.ESCORT,
            self.SCHOOL_ESCPORT,
            self.PURE_ESCROT,
            self.RIDESHARE_ESCORT,
            self.OTHER_ESCORT   )


class RouteMode(Enum):
    WALK = 'walk'
    NETWALK = 'netwalk'
    PTWALK = 'ptwalk'
    BIKE = 'bike'
    CAR = 'car'
    TRAM = 'tram'
    BUS = 'bus'
    PT = 'pt'


class Mode(IntEnum):
    SOV = 1
    HOV2 = 2
    HOV3 = 3
    PASSENGER = 4
    CONV_TRANS_WALK = 5
    CONV_TRANS_KNR = 6
    CONV_TRANS_PNR = 7
    PREM_TRANS_WALK = 8
    PREM_TRANS_KNR = 9
    PREM_TRANS_PNR = 10
    WALK = 11
    BIKE = 12
    TAXI = 13
    SCHOOL_BUS = 14

    def transit(self):
        return self in (
            self.CONV_TRANS_WALK,
            self.CONV_TRANS_KNR,
            self.CONV_TRANS_PNR,
            self.PREM_TRANS_WALK,
            self.PREM_TRANS_KNR,
            self.PREM_TRANS_PNR )

    def vehicle(self):
        return self in (
            self.SOV,
            self.HOV2,
            self.HOV3,
            self.PASSENGER,
            self.TAXI,
            self.SCHOOL_BUS )

    def route_mode(self):
        route_mode = None
        if self.transit():
            route_mode = RouteMode.PT
        elif self.vehicle():
            route_mode = RouteMode.CAR
        elif self == self.WALK:
            route_mode = RouteMode.NETWALK
        elif self == self.BIKE:
            route_mode = RouteMode.BIKE
        return route_mode



class Subpopulation:
    def __init__(self):
        self.households = defaultdict(lambda x: Household(x))
        self.last_trip = None


    def total_agents(self):
        return sum(len(hh.agents) for hh in self.households.values())


    def get_agent(self, trip):
        return self.households[trip.household_id].agents[trip.agent_id]

    
    def parse_trip(self, trip):
        if self.last_trip is not None:
            if self.last_trip.household_id == trip.household_id:
                self.households[self.last_trip.household_id].parse_trip(
                    self.last_trip, trip)
            else:
                self.households[self.last_trip.household_id].parse_trip(
                    self.last_trip, None)
        self.last_trip = trip
    
    def filter(self, valid):
        removed = 0
        for household in self.households.values():
            removed += household.filter(valid)
        return removed

    def clean(self):
        for household in self.households.values():
            household.clean()

    def identify(self):
        for household in self.households.values():
            household.identify()

    def export_agents(self):
        for household in self.households.values():
            agents = household.export_agents()
            for agent in agents:
                yield agent

    def export_activities(self):
        for household in self.households.values():
            activities = household.export_activities()
            for activity in activities:
                yield activity

    def export_legs(self):
        for household in self.households.values():
            legs = household.export_legs()
            for leg in legs:
                yield leg

    def assign_parcels(self, network):
        for household in self.households.values():
            household.assign_parcels(network)



class Network:
    def __init__(self, parcels):
        self.offset = defaultdict(lambda x: 0)
        self.residential_parcels = defaultdict(lambda x: [])
        self.commercial_parcels = defaultdict(lambda x: [])
        self.default_parcels = {}
        self.other_parcels = defaultdict(lambda x: [])

        for apn, maz, kind in parcels:
            if kind == 'residential':
                self.residential_parcels[maz].append(Parcel(apn))
            elif kind == 'commercial':
                self.commercial_parcels[maz].append(Parcel(apn))
            elif kind == 'default':
                self.default_parcels[maz] = Parcel(apn)
            elif kind == 'other':
                self.other_parcels[maz].append(Parcel(apn))

        self.residential_parcels.lock()
        self.commercial_parcels.lock()
        self.other_parcels.lock()

        self.mazs = set(self.default_parcels.keys())


    def random_household_parcel(self, maz):
        parcel = None
        if maz in self.mazs:
            if maz in self.residential_parcels:
                idx = self.offset[maz]
                parcel  = self.residential_parcels[maz][idx]
                self.offset[maz] = (idx + 1) % len(self.residential_parcels[maz])
            elif maz in self.commercial_parcels:
                idx = randint(0, len(self.commercial_parcels[maz]) - 1)
                parcel = self.commercial_parcels[maz][idx]
            elif maz in self.other_parcels:
                idx = randint(0, len(self.other_parcels[maz]) - 1)
                parcel = self.other_parcels[maz][idx]
            elif maz in self.default_parcels:
                parcel = self.default_parcels[maz]
        return parcel


    def random_activity_parcel(self, maz, activity_type=None):
        parcel = None
        if maz in self.mazs:
            if maz in self.commercial_parcels:
                idx = randint(0, len(self.commercial_parcels[maz]) - 1)
                parcel = self.commercial_parcels[maz][idx]
            elif maz in self.other_parcels:
                idx = randint(0, len(self.other_parcels[maz]) - 1)
                parcel = self.other_parcels[maz][idx]
            elif maz in self.residential_parcels:
                idx = randint(0, len(self.residential_parcels[maz]) - 1)
                parcel = self.residential_parcels[maz][idx]
            elif maz in self.default_parcels:
                parcel = self.default_parcels[maz]
        return parcel



class Parcel:
    def __init__(self, apn):
        self.apn = apn



class Vehicle:
    @staticmethod
    def vehicle_hash(mode, household_id=None, agent_id=None, vehicle_id=None):
        vehicle_hash = None
        if mode == Mode.WALK:
            vehicle_hash = f'{household_id}-{agent_id}-walk'
        elif mode == Mode.BIKE:
            vehicle_hash = f'{household_id}-{agent_id}-bike'
        elif mode.transit():
            vehicle_hash = f'{household_id}-{agent_id}-pt'
        elif mode.vehicle() and vehicle_id > 0:
            vehicle_hash = f'{household_id}-{vehicle_id}-car'
                
        return vehicle_hash


    def __init__(self, uuid):
        self.id = uuid



class Trip:
    uuid = 0
    cols = ('household_id', 'agent_id', 'agent_idx', 'party_role', 'party', 
        'origin_taz', 'origin_maz', 'dest_taz',  'dest_maz', 'origin_act', 
        'dest_act', 'mode', 'vehicle_id', 'depart_time', 
        'arrive_time', 'act_duration')
    keys = {key: val for val, key in enumerate(cols)}
    
    @classmethod
    def as_dict(self, trip):
        return {key: trip[val] for val, key in enumerate(self.cols)}
    

    def __init__(self, trip):
        for key, val in self.as_dict(trip).items():
            setattr(self, key, val)



class Household:
    def __init__(self, household):
        self.id = household
        self.parties = {}
        self.agents = {}
        self.vehicles = {}
        self.groups = set()
        self.parcel = None
        self.maz = None

    
    def get_party(self, depart_time, arrive_time, members):
        party_hash = Party.party_hash(depart_time, arrive_time, members)
        party = None
        if party_hash in self.parties:
            party = self.parties[party_hash]
        else:
            party = Party()
            self.parties[party_hash] = party
        return party


    def get_agent(self, agent_id):
        agent = None
        if agent_id in self.agents:
            agent = self.agents[agent_id]
        else:
            agent = Agent(agent_id)
            self.agents[agent_id] = agent
        return agent


    def get_vehicle(self, mode, household_id, agent_id, vehicle_id):
        vehicle_hash = Vehicle.vehicle_hash(mode, household_id, agent_id, vehicle_id)
        vehicle = None
        if vehicle_hash in self.vehicles:
            vehicle = self.vehicles[vehicle_hash]
        else:
            vehicle = Vehicle(vehicle_hash)
            self.vehicles[vehicle_hash] = vehicle
        return vehicle


    def filter(self, valid):
        remove = set()
        for agent in self.agents.values():
            if agent not in remove:
                if not valid(agent):
                    remove = remove.union(agent.dependents())
        for agent in remove:
            agent.safe_delete()
            del self.agents[agent.agent_id]
        return len(remove)


    def clean(self):
        remove = set()
        for key, party in self.parties.items():
            if len(party.agents) == 0:
                remove.add(key)
        for key in remove:
            del self.parties[key]
        self.groups = filter(lambda group: len(group.agents) > 0, self.groups)

    
    def identify(self):
        for party in self.parties.values():
            party.request_id()
        for agent in self.agents.values():
            agent.request_id()
            for activity in agent.activities:
                activity.request_id()
            for leg in agent.legs:
                leg.request_id()
        for group in self.groups:
            group.request_id()


    def export_agents(self):
        for agent_id, agent in self.agents.items():
            yield (
                agent.id,
                self.id,
                agent_id,
                agent.size(),
                agent.uses_vehicle(),
                agent.uses_walk(),
                agent.uses_bike(),
                agent.uses_transit(),
                agent.uses_party())

    
    def export_activities(self):
        for agent in self.agents.values():
            for activity in agent.export_activities():
                yield activity
    
    
    def export_legs(self):
        for agent in self.agents.values():
            for leg in agent.export_legs():
                yield leg
        

    def parse_trip(self, trip, next_trip=None):
        agent = self.get_agent(trip.agent_id)

        mode = Mode(trip.mode)
        vehicle = self.get_vehicle(mode, trip.household_id, 
            trip.agent_id, trip.vehicle_id)
        
        party = self.get_party(trip.depart_time, trip.arrive_time, trip.party)
        if next_trip is None:
            next_party = Party()
        else:
            next_party = self.get_party(next_trip.depart_time, 
                next_trip.arrive_time, next_trip.party)

        if party.origin_group is None:
            party.set_origin_group(Group(trip.origin_maz))
            self.groups.add(party.origin_group)
        if party.dest_group is None:
            if next_party.origin_group is None:
                party.set_dest_group(Group(trip.dest_maz))
                next_party.set_origin_group(party.dest_group)
                self.groups.add(party.dest_group)
            else:
                party.set_dest_group(next_party.origin_group)
        else:
            if next_party.origin_group is None:
                next_party.set_origin_group(party.dest_group)
            elif party.dest_group != next_party.origin_group:
                party.dest_group.merge_group(next_party.origin_group)
                next_party.origin_group = party.dest_group

        if self.maz is None:
            self.maz = trip.origin_maz

        try:
            agent.parse_trip(trip, vehicle, party)
        except Exception:
            breakpoint()

    
    def assign_parcels(self, network):
        self.parcel = network.random_household_parcel(self.maz)
        for group in self.groups:
            parcel = None
            if group.home:
                parcel = self.parcel
            else:
                parcel = network.random_activity_parcel(group.maz)

            group.assign_parcel(parcel)



class Group:
    uuid = 0

    @staticmethod
    def group_hash(time, members):
        agent_ids = members[2:-2].split(',')
        party_hash = None
        if len(agent_ids) > 1:
            party_hash = (time, frozenset(agent_ids))
        return party_hash

    
    def __init__(self, maz):
        self.maz = maz
        self.activities = set()
        self.agents = set()
        self.parties = set()
        self.home = False
        self.id = None

    
    def request_id(self):
        if self.id is None and len(self.agents) > 1:
            Group.uuid += 1
            self.id = Group.uuid


    def add_party(self, party):
        self.parties.add(party)


    def remove_party(self, party):
        self.parties.remove(party)


    def merge_group(self, group):
        self.agents = self.agents.union(group.agents)
        self.activities = self.activities.union(group.activities)
        self.parties = self.parties.union(group.parties)
        self.home |= group.home
        for agent in group.agents:
            agent.groups.remove(group)
            agent.groups.add(self)
        for activity in group.activities:
            activity.group = self
        for party in group.parties:
            party.replace_group(group, self)
        group.agents = set()
        group.activities = set()
        group.parties = set()


    def assign_parcel(self, parcel):
        for activity in self.activities:
            activity.assign_parcel(parcel)

    
    def add_activity(self, activity, agent):
        self.agents.add(agent)
        self.activities.add(activity)
        if activity.activity_type == ActivityType.HOME:
            self.home = True


    def remove_agent(self, agent):
        self.agents.remove(agent)


    def remove_activity(self, activity):
        self.activities.remove(activity)



class Party:
    uuid = 0

    @staticmethod
    def party_hash(depart_time, arrive_time, members):
        agent_ids = members[2:-2].split(',')
        return (depart_time, arrive_time, frozenset(agent_ids))

    
    def __init__(self):
        self.origin_group = None
        self.dest_group = None
        self.legs = set()
        self.agents = set()
        self.driver = None
        self.vehicle = None
        self.mode = None
        self.id = None


    def request_id(self):
        if self.id is None and self.mode != RouteMode.CAR:
            Party.uuid += 1
            self.id = Party.uuid

    
    def add_leg(self, leg, agent):
        if len(self.legs) < 1:
            self.mode = leg.mode.route_mode()
        self.agents.add(agent)
        self.legs.add(leg)


    def assign_vehicles(self):
        for leg in self.legs:
            leg.assign_vehicle(self.vehicle)

    
    def set_driver(self, driver, vehicle):
        self.driver = driver
        self.vehicle = vehicle


    def set_origin_group(self, group):
        if self.origin_group is None:
            self.origin_group = group
            group.add_party(self)


    def set_dest_group(self, group):
        if self.dest_group is None:
            self.dest_group = group
            group.add_party(self)


    def remove_agent(self, agent):
        self.agents.remove(agent)

    
    def remove_leg(self, leg):
        self.legs.remove(leg)


    def replace_group(self, old_group, new_group):
        if self.dest_group == old_group:
            self.dest_group = new_group
        elif self.origin_group == old_group:
            self.origin_group = new_group
        else:
            raise ValueError


class Agent:
    uuid = 0

    def __init__(self, agent_id):
        self.id = None
        self.agent_id = agent_id
        self.activities = []
        self.legs = []
        self.modes = set()
        self.activity_types = set()
        self.mazs = set()
        self.parties = set()
        self.groups = set()

    def request_id(self):
        if self.id is None:
            Agent.uuid += 1
            self.id = Agent.uuid

    def uses_walk(self):
        return Mode.WALK in self.modes

    def uses_vehicle(self):
        return any((mode.vehicle() for mode in self.modes))

    def uses_bike(self):
        return Mode.BIKE in self.modes

    def uses_transit(self):
        return any((mode.transit() for mode in self.modes))

    def uses_party(self):
        return any((len(party.agents) > 1 for party in self.parties))

    def size(self):
        return len(self.activities) + len(self.legs)
    

    def dependents(self, agents=None):
        if agents is None:
            agents = set()
        agents.add(self)
        for party in self.parties:
            if party.driver == self:
                for agent in party.agents:
                    if agent not in agents:
                        agents = agent.dependents(agents)
        return agents


    def safe_delete(self):
        for party in self.parties:
            party.remove_agent(self)
            if party.driver == self:
                party.set_driver(None, None)
        for group in self.groups:
            group.remove_agent(self)
        for leg in self.legs:
            leg.party.remove_leg(leg)
        for activity in self.activities:
            activity.group.remove_activity(activity)
        self.parties = set()
        self.groups = set()
        self.legs = []
        self.activities = []


    def export_activities(self):
        activities = ((
            act.id,
            self.id,
            idx,
            act.activity_type.name.lower(),
            act.parcel.apn,
            act.group.id or 0,
            act.start,
            act.end,
            act.end - act.start
        ) for idx, act in enumerate(self.activities))
        return activities


    def export_legs(self):
        legs = ((
            leg.id,
            self.id,
            idx,
            leg.mode.route_mode().value,
            leg.party.id or 0,
            leg.start,
            leg.end,
            leg.end - leg.start
        ) for idx, leg in enumerate(self.legs))
        return legs


    def last_group(self):
        group = None
        if len(self.activities):
            group = self.activities[-1].group
        return group


    def last_party(self):
        leg = None
        if len(self.legs):
            leg = self.legs[-1].leg
        return leg


    def parse_trip(self, trip, vehicle, party):
        if vehicle is not None:
            party.set_driver(self, vehicle)
                
        if trip.agent_idx == 1:
            activity_type = ActivityType(trip.origin_act)
            start = 14400
            end = int(trip.depart_time * 60) + 14400
            activity = Activity(activity_type, start, end, 
                trip.origin_maz, party.origin_group)
            self.activity_types.add(activity_type)
            self.mazs.add(trip.origin_maz)
            self.activities.append(activity)
            party.origin_group.add_activity(activity, self)
            self.groups.add(party.origin_group)

        # if self.agent_id == 4:
        #     breakpoint()

        assert party.origin_group in self.groups, 'Missing group!'

        mode = Mode(trip.mode)
        start = int(trip.depart_time * 60) + 14400
        end = int(trip.arrive_time * 60) + 14400
        leg = Leg(mode, start, end, party)
        self.modes.add(mode)
        self.legs.append(leg)
        party.add_leg(leg, self)
        self.parties.add(party)

        activity_type = ActivityType(trip.dest_act)
        start = end
        end += int(trip.act_duration * 60)
        activity = Activity(activity_type, start, end, 
            trip.dest_maz, party.dest_group)
        self.activity_types.add(activity_type)
        self.mazs.add(trip.dest_maz)
        self.activities.append(activity)
        party.dest_group.add_activity(activity, self)
        self.groups.add(party.dest_group)



class Activity:
    uuid = 0

    def __init__(self, activity_type, start, end, maz, group):
        self.activity_type = activity_type
        self.start = start
        self.end = end
        self.maz = maz
        self.group = group
        self.parcel = None
        self.id = None


    def request_id(self):
        if self.id is None:
            Activity.uuid += 1
            self.id = Activity.uuid

    
    def assign_parcel(self, parcel):
        self.parcel = parcel



class Leg:
    uuid = 0

    def __init__(self, mode, start, end, party):
        Leg.uuid += 1
        self.id = Leg.uuid
        self.mode = mode
        self.start = start
        self.end = end
        self.party = party
        self.vehicle = None
        self.id = None


    def request_id(self):
        if self.id is None:
            Leg.uuid += 1
            self.id = Leg.uuid


    def assign_vehicle(self, vehicle):
        self.vehicle = vehicle