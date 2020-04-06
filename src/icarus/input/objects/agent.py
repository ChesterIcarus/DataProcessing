
from icarus.input.objects.mode import Mode
from icarus.input.objects.activity_type import ActivityType
from icarus.input.objects.activity import Activity
from icarus.input.objects.leg import Leg


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