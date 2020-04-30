
from icarus.generate.population.types import ActivityType

class Group:
    uuid = 0
    __slots__ = ('maz', 'activities', 'agents', 'parties', 'home', 'id')

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