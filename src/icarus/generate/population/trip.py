

class Trip:
    uuid = 0
    __slots__ = ('household_id', 'agent_id', 'agent_idx', 'party_role', 'party', 
        'origin_taz', 'origin_maz', 'dest_taz',  'dest_maz', 'origin_act', 
        'dest_act', 'mode', 'vehicle_id', 'depart_time', 
        'arrive_time', 'act_duration')    
    

    def __init__(self, trip):
        self.household_id, self.agent_id, self.agent_idx, self.party_role, \
            self.party, self.origin_taz, self.origin_maz, self.dest_taz, \
            self.dest_maz, self.origin_act, self.dest_act, self.mode, \
            self.vehicle_id, self.depart_time, self.arrive_time, \
            self.act_duration = trip
