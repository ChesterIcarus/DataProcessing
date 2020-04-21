
from icarus.input.objects.household import Household
from icarus.util.general import defaultdict

class Population:
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