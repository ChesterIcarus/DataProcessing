
from collections import defaultdict
from netCDF4 import Dataset             # pylint: disable=no-name-in-module
from pyproj import Transformer
from math import cos, pi
from scipy.spatial import Voronoi       # pylint: disable=no-name-in-module

from icarus.network.parse.exposure.database import DaymetParserDatabaseHandle
from icarus.util.print import PrintUtil as pr
from icarus.util.config import ConfigUtil


class DaymetParser:
    def __init__(self, database):
        self.database = DaymetParserDatabaseHandle(database)


    @staticmethod
    def encode_polygon(points):
        pts = ', '.join([f'{x} {y}' for x, y in (points + [points[0]])])
        return f'POLYGON(({pts}))'


    @staticmethod
    def encode_point(x, y):
        return f'POINT({x} {y})'


    @staticmethod
    def iterpolation(tmin, tmax, tdawn, tpeak):
        return lambda t: (
            (tmax+tmin)/2-(tmax-tmin)/2*cos(pi*(tdawn-t)/(24+tdawn-tpeak)) if t < tdawn
            else (tmax+tmin)/2+(tmax-tmin)/2*cos(pi*(tpeak-t)/(tpeak-tdawn)) if t < tpeak
            else (tmax+tmin)/2-(tmax-tmin)/2*cos(pi*(24+tdawn-t)/(24+tdawn-tpeak)))


    @classmethod
    def process_vor(self, vor, centroids):
        for point in zip(centroids, vor.points, vor.point_region):
            if -1 not in vor.regions[point[2]]:
                centroid = point[0]
                center = self.encode_point(*point[1])
                region = self.encode_polygon([vor.vertices[i] 
                    for i in vor.regions[point[2]]])
                yield centroid + (region, center)
        

    @classmethod
    def validate_config(self, configpath, specspath):
        config = ConfigUtil.load_config(configpath) 
        specs = ConfigUtil.load_specs(specspath)
        config = ConfigUtil.verify_config(specs, config)

        steps = config['select']['steps']
        if 86400 % steps:
            raise ValueError('Parameter "run.steps" must divide 86400 but '
                f'found {steps} (86400 % {steps} = {86400 % steps}).')

        if len(config['run']['tmin']) != len(config['run']['tmax']):
            raise RuntimeError('The number of "tmin" and "tmax" files must match.')

        files = zip(config['run']['tmax'], config['run']['tmin'])
        for tmax_file, tmin_file in files:
            tmaxnc = Dataset(tmax_file, 'r')
            tminnc = Dataset(tmin_file, 'r')
            if tmaxnc.variables['tmax'].shape != tminnc.variables['tmin'].shape:
                raise RuntimeError(f'Tmax file "{tmax_file}" dimension does not '
                    f'match with that of tmin file "{tmin_file}".')

        return config


    def create_tables(self, *tables, force=False):
        if not force:
            exists = self.database.table_exists(*tables)
            if len(exists):
                exists = '", "'.join(exists)
                cond = pr.print(f'Table{"s" if len(exists) > 1 else ""} '
                    f'"{exists}" already exist in database '
                    f'"{self.database.db}". Drop and continue? [Y/n] ', 
                    inquiry=True, time=True, force=True)
                if not cond:
                    pr.print('User chose to terminate process.', time=True)
                    raise RuntimeError
        for table in tables:
            self.database.create_table(table)
    

    def run(self, config):
        pr.print('Preallocating files/tables for module run.', time=True)
        self.create_tables('temperatures', 'centroids', force=config['run']['force'])

        day = config['select']['day']
        steps = config['select']['steps']
        files = zip(config['run']['tmax'], config['run']['tmin'])

        centroids = []
        points = []
        temperatures = []
        temps = {}
        total = 0
        centroid_id = 0
        temperature_id = 0
        n = 1

        transformer = Transformer.from_crs('epsg:4326', 'epsg:2223', always_xy=True)

        pr.print('Loading netCDF files for parsing.', time=True)
        for tmax_file, tmin_file in files:
            tmaxnc = Dataset(tmax_file, 'r')
            tminnc = Dataset(tmin_file, 'r')
            total += tmaxnc.variables['tmax'].shape[1] * \
                tmaxnc.variables['tmax'].shape[2]
            tmaxnc.close()
            tminnc.close()

        pr.print('Iterating over daymet data and parsing.', time=True)
        pr.print(f'Total centroids to parse: {total}.', time=True)
        files = zip(config['run']['tmax'], config['run']['tmin'])

        for tmax_file, tmin_file in files:
            tmaxnc = Dataset(tmax_file, 'r')
            tminnc = Dataset(tmin_file, 'r')

            lons = tmaxnc.variables['lon']
            lats = tmaxnc.variables['lat']
            shape = tmaxnc.variables['tmax'].shape

            tmaxs = tmaxnc.variables['tmax'][day]
            tmins = tminnc.variables['tmin'][day]

            for i in range(shape[1]):
                for j in range(shape[2]):
                    tmax = tmaxs[i][j]
                    tmin = tmins[i][j]

                    if tmax != -9999.0:
                        point = transformer.transform(lons[i][j], lats[i][j])
                        idx = f'{tmax}-{tmin}'

                        if idx not in temps:
                            temp = self.iterpolation(tmin, tmax, 5, 15)
                            temperatures.extend([(
                                temperature_id,
                                step,
                                int(86400 * step / steps),
                                temp(24*step/steps)) for step in range(steps)])
                            temps[idx] = temperature_id
                            temperature_id += 1
                        
                        centroids.append((centroid_id, temps[idx]))
                        points.append(point)
                        centroid_id += 1

                        if centroid_id == n:
                            pr.print(f'Found centroid {centroid_id}.', time=True)
                            n <<= 1

            tmaxnc.close()
            tminnc.close()
        
        del tmaxnc
        del tminnc

        if centroid_id != n:
            pr.print(f'Found centroid {centroid_id}.', time=True)

        pr.print(f'Found {centroid_id} valid centroids (locations) and '
            f'{temperature_id} unique temperature profiles.', time=True)

        pr.print(f'Calculating Voronoi polygons from centroids.', time=True)
        vor = Voronoi(points)
        centroids = self.process_vor(vor, centroids)

        pr.print('Pushing centroids and temperatures to the database.', time=True)
        self.database.write_rows(temperatures, 'temperatures')
        self.database.write_centroids(centroids)
        
        if config['run']['create_idxs']:
            pr.print('Creating indexes on module tables.', time=True)
            self.database.create_all_idxs('centroids')
            self.database.create_all_idxs('temperatures')
