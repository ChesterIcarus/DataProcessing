
import logging as log

from shapely.geometry import Polygon
from random import randint
from icarus.util.sqlite import SqliteUtil
from icarus.util.general import defaultdict, counter


class Parcel:
    __slots__ = ('apn',)

    def __init__(self, apn: str):
        self.apn = apn


class Region:
    __slots__ = ('polygon',)

    @staticmethod
    def region_coords(region: str):
        coords = []
        points = region[10:-2].split(', ')
        for point in points:
            x, y = point.split(' ')
            coords.append((float(x) * 0.3048, float(y) * 0.3048))
        return coords
    
    def __init__(self, polygon: str):
        self.polygon = Polygon(self.region_coords(polygon))


class Network:
    def __init__(self, database: SqliteUtil):
        self.database = database
        self.loaded = False

    
    def fetch_parcels(self):
        self.database.cursor.execute(f'''
            SELECT
                apn,
                maz,
                type
            FROM parcels
            ORDER BY 
                RANDOM(); ''')

        return self.database.cursor.fetchall()

    
    def fetch_regions(self):
        query = '''
            SELECT
                maz,
                region
            FROM regions;   '''
        self.database.cursor.execute(query)
        return self.database.cursor.fetchall()


    def load_parcels(self):
        parcels = self.fetch_parcels()
        self.residential_parcels = defaultdict(lambda x: [])
        self.commercial_parcels = defaultdict(lambda x: [])
        self.default_parcels = {}
        self.other_parcels = defaultdict(lambda x: [])

        for apn, maz, kind in counter(parcels, 'Loading parcel %s.'):
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
        self.offset = defaultdict(lambda x: 0)


    def load_regions(self):
        regions = self.fetch_regions()
        self.regions = {}
        for maz, polygon in counter(regions, 'Loading region %s.'):
            self.regions[maz] = Region(polygon)
        return regions


    def load_network(self):
        log.info('Loading parcel data.')
        self.load_parcels()
        log.info('Loading region data.')
        self.load_regions()
        self.loaded = True


    def minimum_distance(self, maz1: str, maz2: str) -> float:
        return self.regions[maz1].polygon.distance(self.regions[maz2].polygon)


    def random_household_parcel(self, maz:str) -> Parcel:
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


    def random_activity_parcel(self, maz: str) -> Parcel:
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
