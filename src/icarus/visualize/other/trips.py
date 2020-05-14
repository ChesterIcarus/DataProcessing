
import logging as log
import seaborn as sns
from pyproj import Transformer
from shapely.geometry import Polygon

from icarus.generate.population.types import Mode
from icarus.util.sqlite import SqliteUtil
from icarus.util.general import defaultdict


def region_coords(region):
    result = []
    points = region[10:-2].split(', ')
    for point in points:
        x, y = point.split(' ')
        result.append((float(x) * 0.3048, float(y) * 0.3048))
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


    def get_trips(self, bin_size=1000000):
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
            break

    
    def plot_histogram(self, data, title, xaxis, yaxis, save, trim):
        options = { 'cumulative': True }
        axes = sns.distplot(data, hist_kws=options, kde_kws=options)
        axes.set_title(title)
        axes.set_xlabel(xaxis)
        axes.set_ylabel(yaxis)
        # plot = axes.get_figure()
        # plot.savefig(f'{save}.png', bbox_inches='tight')
        # plot.clf()
        # axes.set(ylim=(0.5, 1), xlim=(0, trim))
        plot = axes.get_figure()
        plot.savefig(f'{save}_trimmed.png', bbox_inches='tight')
        plot.clf()


    def minimum_speed(self):
        log.info('Running lower bound speed test.')
        
        log.info('Loading regions.')
        regions = self.load_regions()
        distances = {}

        walk, bike, transit, vehicle = [], [], [], []

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
                distance = regions[origin_maz].distance(regions[dest_maz])
                distances[key] = distance
            else:
                continue

            speed = distance / duration / 60

            if mode == Mode.WALK:
                walk.append(speed)
            elif mode == Mode.BIKE:
                bike.append(speed)
            elif mode.transit():
                transit.append(speed)
            elif mode.vehicle():
                vehicle.append(speed)

            count += 1
            if count == n:
                log.info(f'Analyzing trip {count}.')
                n <<= 1

        if count != n >> 1:
            log.info(f'Analyzing trip {count}.')

        del distances

        log.info('Generating charts.')
        log.info('Generating walking chart.')
        self.plot_histogram(walk, 'Walking Trip Minimum Speed', 'Speed (m/s)', 
            'Cummulative Proportion', 'result/abm_walking_speed_dist', 100)
        log.info('Generating biking chart.')
        self.plot_histogram(bike, 'Biking Minimum Trip Speed', 'Speed (m/s)',
            'Cummulative Proportion', 'result/abm_biking_speed_dist', 100)
        log.info('Generating transit chart.')
        self.plot_histogram(transit, 'Bus/Rail Trip Minimum Speed', 'Speed (m/s)',
            'Cummulative Proportion', 'result/abm_transit_speed_dist', 100)
        log.info('Generating vehicular chart.')
        self.plot_histogram(vehicle, 'Vehicle Trip Minimum Speed', 'Speed (m/s)',
            'Cummulative Proportion', 'result/abm_vehicle_speed_dist', 100)

        log.info('Complete.')