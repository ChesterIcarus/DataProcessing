
from collections import defaultdict
from netCDF4 import Dataset
from pyproj import Proj, transform
from math import cos, pi

from icarus.exposure.parse.database import DaymetParserDatabaseHandle
from icarus.util.print import Printer as pr


class DaymetParser:
    def __init__(self, database):
        self.database = DaymetParserDatabaseHandle(database)

    def create_tables(self):
        pass

    def encode_polygon(self, points):
        pass

    def encode_point(self, x, y):
        return f'POINT({x} {y})'


    def iterpolation(self, tmin, tmax, tdawn, tpeak):
        return lambda t: (
            (tmax+tmin)/2-(tmax-tmin)/2*cos(pi*(tdawn-t)/(24+tdawn-tpeak)) if t < tdawn
            else (tmax+tmin)/2+(tmax-tmin)/2*cos(pi*(tpeak-t)/(tpeak-tdawn)) if t < tpeak
            else (tmax+tmin)/2-(tmax-tmin)/2*cos(pi*(24+tdawn-t)/(24+tdawn-tpeak)))
        

    def run(self, config, silent=False):
        pr.print('Loading netCDF files for parsing.', time=True)

        self.database.create_table('temperatures')
        self.database.create_table('centroids')

        day = config['day']
        steps = config['steps']

        centroids = []
        centroid_id = 0
        temperatures = []
        temperature_id = 0
        temps = {}

        srccrs = Proj(init='epsg:4326')
        tarcrs = Proj(init='epsg:2223')

        tmaxnc = Dataset(config['tmax_file'], 'r')
        tminnc = Dataset(config['tmin_file'], 'r')

        lons = tmaxnc.variables['lon']
        lats = tmaxnc.variables['lat']
        shape = tmaxnc.variables['tmax'].shape

        tmaxs = tmaxnc.variables['tmax']
        tmins = tminnc.variables['tmin']

        pr.print('Iterating over daymet data and parsing.', time=True)
        pr.print(f'Total centroids to parse: {shape[1] * shape[2]}.', time=True)
        n = 1

        for i in range(shape[1]):
            for j in range(shape[2]):
                lat = lats[i][j]
                lon = lons[i][j]
                tmax = tmaxs[day][i][j]
                tmin = tmins[day][i][j]
                point = self.encode_point(*transform(srccrs, tarcrs, lon, lat))
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
                
                centroids.append((centroid_id, temps[idx], point))
                centroid_id += 1

                if centroid_id == n:
                    pr.print(f'Found centroid {centroid_id}.', time=True)
                    n = n << 1


        pr.print(f'Found {len(centroids)} centroids (locations) and '
            f'{len(temperatures)} unique temperature profiles.', time=True)
        pr.print('Pushing them to the database.', time=True)
        self.database.write_rows(temperatures, 'temperatures')
        self.database.write_geom_rows(centroids, 'centroids', geo=1, srid=2223)
        
        self.database.create_all_idxs('centroids')
        self.database.create_all_idxs('temperatures')