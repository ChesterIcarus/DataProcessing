

class Vehicle:
    __slots__ = ('id', 'mode', 'agents', 'exposure', 'temperature', 'link', 'time')

    def __init__(self, uuid, mode, time, link, temperature=None):
        self.id = uuid
        self.mode = mode
        self.agents = set()
        self.exposure = 0
        self.temperature = temperature
        self.link = link
        self.time = time


    def enter_link(self, time, link):
        self.link = link
        self.time = time

    
    def leave_link(self, time, link):
        if self.time is not None:
            if self.temperature is None:
                self.exposure += self.link.get_exposure(self.time, time)
            else:
                self.exposure += self.temperature * (time - self.time)
        self.time = time
        self.link = link


    def add_agent(self, agent):
        agent.expose(-self.exposure)
        self.agents.add(agent)
    

    def remove_agent(self, agent):
        agent.active_leg.active_link = self.link
        agent.active_leg.active_time = self.time
        agent.expose(self.exposure)
        self.agents.remove(agent)
        
