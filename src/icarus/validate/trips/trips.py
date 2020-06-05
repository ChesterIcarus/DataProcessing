
import logging as log
from pyproj import Transformer
from shapely.wkt import loads
from shapely.geometry import Polygon

from icarus.generate.population.types import Mode
from icarus.util.sqlite import SqliteUtil
from icarus.util.general import defaultdict


def region_coords(region):
    result = []
    points = region[10:-2].split(', ')
    for point in points:
        x, y = point.split(' ')
        result.append((float(x), float(y)))
    return result


class Trips:
    def __init__(self, database: SqliteUtil):
        self.database = database


    def get_regions(self):
        query = '''
            SELECT
                maz,
                region
            FROM regions;   '''
        self.database.cursor.execute(query)
        return self.database.cursor.fetchall()

    
    def load_regions(self):
        regions = {}

        n = 1
        count = 0
        for maz, polygon in self.get_regions():
            coords = region_coords(polygon)
            shape = Polygon(coords)
            setattr(shape, 'maz', maz)
            regions[maz] = shape

            count += 1
            if count == n:
                log.info(f'Loading region {count}.')
                n <<= 1

        if count != n >> 1:
            log.info(f'Loading region {count}.')
        
        return regions


    def get_trips(self, bin_size=100000):
        query = '''
            SELECT
                origMaz,
                destMaz,
                mode,
                isamAdjArrMin - isamAdjDepMin
            FROM trips; '''
        self.database.cursor.execute(query)
        trips = self.database.cursor.fetchmany(bin_size)
        while len(trips):
            for trip in trips:
                yield trip
            trips = self.database.cursor.fetchmany(bin_size)
            

    def minimum_distance(self):
        log.info('Running lower bound speed test.')
        
        log.info('Loading regions.')
        regions = self.load_regions()
        distances = {}
        bad_walk, bad_bike, bad_transit, bad_vehicle, bad_maz = 0, 0, 0, 0, 0
        walk, bike, transit, vehicle = 0, 0, 0, 0

        log.info('Iterating over ABM population trips.')
        n = 1
        count = 0
        for trip in self.get_trips():
            origin_maz, dest_maz, mode, duration = trip
            mode = Mode(mode)
            key = frozenset((origin_maz, dest_maz))
            
            if origin_maz == dest_maz:
                distance = 0
            elif key in distances:
                distance = distances[key]
            elif origin_maz in regions and dest_maz in regions:
                distance = regions[origin_maz].distance(regions[dest_maz]) * 0.3048
                distances[key] = distance
            else:
                distance = 0
                bad_maz += 1

            if duration > 0:
                speed = distance / duration / 60
            elif distance == 0:
                speed = 0
            else:
                speed = float('inf')
                

            if mode == Mode.WALK:
                walk += 1
                if speed > 3:
                    bad_walk += 1
            elif mode == Mode.BIKE:
                bike += 1
                if speed > 10:
                    bad_bike += 1
            elif mode.transit():
                transit += 1
                if speed > 30:
                    bad_transit += 1
            elif mode.vehicle():
                vehicle += 1
                if speed > 35:
                    bad_vehicle += 1

            count += 1
            if count == n:
                log.info(f'Analyzing trip {count}.')
                n <<= 1

            if count == 2000000:
                break

        if count != n >> 1:
            log.info(f'Analyzing trip {count}.')

        bad_total = sum((bad_walk, bad_bike, bad_transit, bad_vehicle, bad_maz))

        log.info('Lower bound speed test results:\n'
            '===================================================\n'
            f'bad walks: {bad_walk} ({bad_walk / walk * 100}%)\n'
            f'bad bikes: {bad_bike} ({bad_bike / bike * 100}%)\n'
            f'bad transits: {bad_transit} ({bad_transit / transit * 100}%)\n'
            f'bad vehicles: {bad_vehicle} ({bad_vehicle / vehicle * 100}%)\n'
            f'bad maz: {bad_maz} ({bad_maz / count * 100}%)\n'
            f'bad total: {bad_total} ({bad_total / count * 100}%)\n)'
            '===================================================')
