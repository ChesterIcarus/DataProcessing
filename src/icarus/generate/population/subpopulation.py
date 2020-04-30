
from typing import Dict, Callable, Iterator
from icarus.generate.population.network import Network
from icarus.generate.population.household import Household
from icarus.generate.population.trip import Trip
from icarus.generate.population.agent import Agent, Activity, Leg
from icarus.util.general import defaultdict

class Subpopulation:
    def __init__(self):
        self.households: Dict[int, Household] = defaultdict(lambda x: Household(x))
        self.last_trip: Trip = None


    def total_agents(self) -> int:
        return sum(len(hh.agents) for hh in self.households.values())


    def get_agent(self, trip: Trip) -> Agent:
        return self.households[trip.household_id].agents[trip.agent_id]

    
    def parse_trip(self, trip: Trip):
        if self.last_trip is not None:
            if self.last_trip.household_id == trip.household_id:
                self.households[self.last_trip.household_id].parse_trip(
                    self.last_trip, trip)
            else:
                self.households[self.last_trip.household_id].parse_trip(
                    self.last_trip, None)
        self.last_trip = trip
    
    
    def filter(self, valid: Callable[[Agent], bool]) -> int:
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

    def export_agents(self) -> Iterator[Agent]:
        for household in self.households.values():
            agents = household.export_agents()
            for agent in agents:
                yield agent

    def export_activities(self) -> Iterator[Activity]:
        for household in self.households.values():
            activities = household.export_activities()
            for activity in activities:
                yield activity

    def export_legs(self) -> Iterator[Leg]:
        for household in self.households.values():
            legs = household.export_legs()
            for leg in legs:
                yield leg

    def assign_parcels(self, network: Network):
        for household in self.households.values():
            household.assign_parcels(network)