
from icarus.input.objects.mode import Mode

class Vehicle:
    @staticmethod
    def vehicle_hash(mode, household_id=None, agent_id=None, vehicle_id=None):
        vehicle_hash = None
        if mode == Mode.WALK:
            vehicle_hash = f'{household_id}-{agent_id}-walk'
        elif mode == Mode.BIKE:
            vehicle_hash = f'{household_id}-{agent_id}-bike'
        elif mode.transit():
            vehicle_hash = f'{household_id}-{agent_id}-pt'
        elif mode.vehicle() and vehicle_id > 0:
            vehicle_hash = f'{household_id}-{vehicle_id}-car'
                
        return vehicle_hash


    def __init__(self, uuid):
        self.id = uuid