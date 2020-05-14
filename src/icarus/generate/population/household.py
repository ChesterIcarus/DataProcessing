
from typing import Dict
from icarus.generate.population.agent import Agent
from icarus.generate.population.party import Party
from icarus.generate.population.vehicle import Vehicle
from icarus.generate.population.group import Group
from icarus.generate.population.types import Mode


class Household:
    __slots__ = ('id', 'parties', 'agents', 'vehicles', 'groups', 'parcel', 'maz')
    
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
                    remove.update(agent.dependents())
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
