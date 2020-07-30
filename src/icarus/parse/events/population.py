
import logging as log

from icarus.util.general import defaultdict
from icarus.parse.events.agent import Agent
from icarus.parse.events.vehicle import Vehicle
from icarus.parse.events.network import Network
from icarus.parse.events.types import NetworkMode, LegMode, ActivityType


class Population:
    def __init__(self, network: Network):
        self.network = network
        self.agents = network.agents
        self.vehicles = {}


    def get_agent(self, agent_id):
        agent = None
        if agent_id in self.agents:
            agent = self.agents[agent_id]
        else:
            agent = Agent(agent_id)
            self.agents[agent_id] = agent
        return agent


    def get_vehicle(self, vehicle_id):
        vehicle = None
        if vehicle_id in self.vehicles:
            vehicle = self.vehicles[vehicle_id]
        else:
            vehicle = Vehicle(vehicle_id)
            self.vehicles[vehicle_id] = vehicle
        return vehicle


    def parse_event(self, event):
        action = event.get('type')
        time = int(float(event.get('time')))
        agent = None

        if action == 'TransitDriverStarts':
            agent = self.get_agent(event.get('driverId'))

        elif action == 'left link':
            pass
            
        elif action == 'entered link':
            pass

        elif action == 'PersonEntersVehicle':
            pass

        elif action == 'PersonLeavesVehicle':
            pass

        elif action == 'actstart':
            link = self.network.links[event.get('link')]
            agent = self.get_agent(event.get('person'))
            activity_type = ActivityType(event.get('actType'))
            agent.start_activity(time, link, activity_type)

        elif action == 'actend':
            link = self.network.links[event.get('link')]
            agent = self.get_agent(event.get('person'))
            activity_type = ActivityType(event.get('actType'))
            agent.end_activity(time, link, activity_type)

        elif action == 'departure':
            link = self.network.links[event.get('link')]
            agent = self.get_agent(event.get('person'))
            leg_mode = LegMode(event.get('legMode'))
            agent.start_leg(time, link, leg_mode)

        elif action == 'arrival':
            link = self.network.links[event.get('link')]
            agent = self.get_agent(event.get('person'))
            leg_mode = LegMode(event.get('legMode'))
            agent.end_leg(time, link, leg_mode)

        elif action == 'travelled':
            agent = self.get_agent(event.get('person'))
            agent.travel(time)

        elif action == 'stuckAndAbort':
            agent = self.get_agent(event.get('person'))
            agent.abort_plan()

        else:
            pass

    
    def export_agents(self, condition=None):
        for agent in self.agents.values():
            if str(agent.id).isdigit():
                yield (
                    agent.id,
                    agent.size(),
                    int(agent.abort),
                    None 
                )
    

    def export_activities(self):
        for agent in self.agents.values():
            if str(agent.id).isdigit():
                for activity in agent.export_activities():
                    yield activity

    
    def export_legs(self):
        for agent in self.agents.values():
            if str(agent.id).isdigit():
                for leg in agent.export_legs():
                    yield leg

    
    def export_events(self):
        for agent in self.agents.values():
            if str(agent.id).isdigit():
                for event in agent.export_events():
                    yield event


    def filter_agents(self, condition):
        remove = set()
        for agent in self.agents.values():
            if not condition(agent):
                remove.add(agent.id)
        for uuid in remove:
            del self.agents[uuid]


    def cleanup(self, time):
        for agent in self.agents.values():
            if agent.active_activity is not None:
                if agent.active_activity.activity_type == ActivityType.HOME:
                    agent.end_activity(time, link = None, 
                        activity_type = ActivityType.HOME)

