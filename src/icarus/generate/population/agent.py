
from __future__ import annotations
from typing import Set, List, Iterator, Tuple

from icarus.generate.population.party import Party
from icarus.generate.population.trip import Trip
from icarus.generate.population.group import Group
from icarus.generate.population.vehicle import Vehicle
from icarus.generate.population.network import Parcel
from icarus.generate.population.types import ActivityType, Mode


class Leg:
    uuid = 0
    __slots__ = ('id', 'mode', 'start', 'end', 'party', 'vehicle')

    def __init__(self, mode: Mode, start: int, end: int, party: Party):
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


    def assign_vehicle(self, vehicle: Vehicle):
        self.vehicle = vehicle



class Activity:
    uuid = 0
    __slots__ = ('activity_type', 'start', 'end', 'maz', 'group', 'parcel', 'id')

    def __init__(self, activity_type: ActivityType, start: int, end:int,
            maz: int, group: Group):
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

    
    def assign_parcel(self, parcel: Parcel):
        self.parcel = parcel



class Agent:
    uuid = 0
    __slots__ = ('agent_id', 'activities', 'legs', 'modes', 'activity_types',
            'mazs', 'parties', 'groups', 'id')

    def __init__(self, agent_id: str):
        self.agent_id: str = agent_id
        self.activities: List[Activity] = []
        self.legs: List[Leg] = []
        self.modes: Set[Mode] = set()
        self.activity_types: Set[ActivityType] = set()
        self.mazs: Set[int] = set()
        self.parties: Set[Party] = set()
        self.groups: Set[Group] = set()
        self.id: int = None

    def request_id(self):
        if self.id is None:
            Agent.uuid += 1
            self.id = Agent.uuid

    def uses_walk(self) -> bool:
        return Mode.WALK in self.modes

    def uses_vehicle(self) -> bool:
        return any((mode.vehicle() for mode in self.modes))

    def uses_bike(self) -> bool:
        return Mode.BIKE in self.modes

    def uses_transit(self) -> bool:
        return any((mode.transit() for mode in self.modes))

    def uses_party(self) -> bool:
        return any((len(party.agents) > 1 for party in self.parties))

    def size(self) -> int:
        return len(self.activities) + len(self.legs)
    

    def dependents(self, agents: Set[Agent] = None) -> Set[Agent]:
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


    def export_activities(self) -> Iterator[Tuple]:
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


    def export_legs(self) -> Iterator[Tuple]:
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


    def last_group(self) -> Group:
        group = None
        if len(self.activities):
            group = self.activities[-1].group
        return group


    def last_party(self) -> Party:
        leg = None
        if len(self.legs):
            leg = self.legs[-1].leg
        return leg


    def parse_trip(self, trip: Trip, vehicle: Vehicle, party: Party):
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
