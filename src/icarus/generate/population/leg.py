
class Leg:
    uuid = 0

    def __init__(self, mode, start, end, party):
        Leg.uuid += 1
        self.id = Leg.uuid
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


    def assign_vehicle(self, vehicle):
        self.vehicle = vehicle