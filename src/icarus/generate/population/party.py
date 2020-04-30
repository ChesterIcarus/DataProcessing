
from typing import Set

from icarus.generate.population.types import RouteMode


class Party:
    uuid = 0
    __slots__ = ('origin_group', 'dest_group', 'legs', 'agents', 'driver',
        'vehicle', 'mode', 'id')

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
        if self.id is None and len(self.agents) > 1:
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