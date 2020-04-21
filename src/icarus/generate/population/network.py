
from random import randint
from icarus.util.general import defaultdict
from icarus.input.objects.parcel import Parcel

class Network:
    def __init__(self, parcels):
        self.offset = defaultdict(lambda x: 0)
        self.residential_parcels = defaultdict(lambda x: [])
        self.commercial_parcels = defaultdict(lambda x: [])
        self.default_parcels = {}
        self.other_parcels = defaultdict(lambda x: [])

        for apn, maz, kind in parcels:
            if kind == 'residential':
                self.residential_parcels[maz].append(Parcel(apn))
            elif kind == 'commercial':
                self.commercial_parcels[maz].append(Parcel(apn))
            elif kind == 'default':
                self.default_parcels[maz] = Parcel(apn)
            elif kind == 'other':
                self.other_parcels[maz].append(Parcel(apn))

        self.residential_parcels.lock()
        self.commercial_parcels.lock()
        self.other_parcels.lock()

        self.mazs = set(self.default_parcels.keys())


    def random_household_parcel(self, maz):
        parcel = None
        if maz in self.mazs:
            if maz in self.residential_parcels:
                idx = self.offset[maz]
                parcel  = self.residential_parcels[maz][idx]
                self.offset[maz] = (idx + 1) % len(self.residential_parcels[maz])
            elif maz in self.commercial_parcels:
                idx = randint(0, len(self.commercial_parcels[maz]) - 1)
                parcel = self.commercial_parcels[maz][idx]
            elif maz in self.other_parcels:
                idx = randint(0, len(self.other_parcels[maz]) - 1)
                parcel = self.other_parcels[maz][idx]
            elif maz in self.default_parcels:
                parcel = self.default_parcels[maz]
        return parcel


    def random_activity_parcel(self, maz, activity_type=None):
        parcel = None
        if maz in self.mazs:
            if maz in self.commercial_parcels:
                idx = randint(0, len(self.commercial_parcels[maz]) - 1)
                parcel = self.commercial_parcels[maz][idx]
            elif maz in self.other_parcels:
                idx = randint(0, len(self.other_parcels[maz]) - 1)
                parcel = self.other_parcels[maz][idx]
            elif maz in self.residential_parcels:
                idx = randint(0, len(self.residential_parcels[maz]) - 1)
                parcel = self.residential_parcels[maz][idx]
            elif maz in self.default_parcels:
                parcel = self.default_parcels[maz]
        return parcel