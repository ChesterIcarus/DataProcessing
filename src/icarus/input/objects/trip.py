

class Trip:
    uuid = 0
    cols = ('household_id', 'agent_id', 'agent_idx', 'party_role', 'party', 
        'origin_taz', 'origin_maz', 'dest_taz',  'dest_maz', 'origin_act', 
        'dest_act', 'mode', 'vehicle_id', 'depart_time', 
        'arrive_time', 'act_duration')
    keys = {key: val for val, key in enumerate(cols)}
    
    @classmethod
    def as_dict(self, trip):
        return {key: trip[val] for val, key in enumerate(self.cols)}
    

    def __init__(self, trip):
        for key, val in self.as_dict(trip).items():
            setattr(self, key, val)