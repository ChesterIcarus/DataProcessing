
import logging as log
from xml.etree.ElementTree import tostring
from icarus.util.general import defaultdict
from icarus.output.objects.agent import Agent
from icarus.output.objects.vehicle import Vehicle
from icarus.output.objects.network import Network
from icarus.output.objects.types import VehicleMode, ActivityType, LegMode
from dataclasses import dataclass

class Population:
    def __init__(self, network):
        self.network = network
        self.agents = network.agents
        self.vehicles = {}


    def get_agent(self, agent_id):
        agent = None
        if agent_id in self.agents:
            agent = self.agents[agent_id]
        else:
            agent = Agent(agent_id)
            self.agents[agent_id] = Agent(agent_id)
        return agent


    def get_vehicle(self, vehicle_id, time, link):
        vehicle = None
        if vehicle_id in self.vehicles:
            vehicle = self.vehicles[vehicle_id]
        else:
            mode = VehicleMode.parse(vehicle_id)
            temperature = 25.5 if not mode.outdoors() else None
            vehicle = Vehicle(vehicle_id, mode, time, link, temperature)
            self.vehicles[vehicle_id] = vehicle
        return vehicle


    def parse_event(self, event):
        action = event.get('type')
        time = int(float(event.get('time')))
        agent = None

        if action == 'TransitDriverStarts':
            agent = self.get_agent(event.get('driverId'))

        elif action == 'left link':
            link = self.network.links[event.get('link')]
            vehicle = self.get_vehicle(event.get('vehicle'), time, link)
            vehicle.leave_link(time, link)
            
        elif action == 'entered link':
            link = self.network.links[event.get('link')]
            vehicle = self.get_vehicle(event.get('vehicle'),time, link)
            vehicle.enter_link(time, link)

        elif action == 'PersonEntersVehicle':
            agent = self.get_agent(event.get('person'))
            link = agent.active_leg.active_link
            vehicle = self.get_vehicle(event.get('vehicle'), time, link)
            vehicle.add_agent(agent)

        elif action == 'PersonLeavesVehicle':
            agent = self.get_agent(event.get('person'))
            link = agent.active_leg.active_link
            vehicle = self.get_vehicle(event.get('vehicle'), time, link)
            vehicle.remove_agent(agent)

        elif action == 'actstart':
            link = self.network.links[event.get('link')]
            agent = self.get_agent(event.get('person'))
            activity_type = ActivityType.parse(event.get('actType'))
            agent.start_activity(time, activity_type, link)

        elif action == 'actend':
            link = self.network.links[event.get('link')]
            agent = self.get_agent(event.get('person'))
            agent.end_activity(time, link)

        elif action == 'departure':
            link = self.network.links[event.get('link')]
            agent = self.get_agent(event.get('person'))
            mode = LegMode(event.get('legMode'))
            agent.depart(time, mode, link)

        elif action == 'arrival':
            link = self.network.links[event.get('link')]
            agent = self.get_agent(event.get('person'))
            agent.arrive(time, link)

        elif action == 'stuckAndAbort':
            pass

        else:
            pass

    
    def export_agents(self):
        for agent in self.agents.values():
            yield (
                agent.id,
                agent.size(),
                agent.exposure())
    

    def export_activities(self):
        for agent in self.agents.values():
            for activity in agent.export_activities():
                yield activity

    
    def export_legs(self):
        for agent in self.agents.values():
            for leg in agent.export_legs():
                yield leg

    
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
                    agent.end_activity(time)

