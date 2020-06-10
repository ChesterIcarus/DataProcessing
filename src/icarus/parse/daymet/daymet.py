
import logging as log
from netCDF4 import Dataset             # pylint: disable=no-name-in-module
from scipy.spatial import Voronoi       # pylint: disable=no-name-in-module
from pyproj import Transformer
from math import cos, pi
from shapely.geometry import Polygon, Point
from shapely.wkt import dumps

from icarus.util.sqlite import SqliteUtil
from icarus.util.file import exists


class Daymet:
    @staticmethod
    def iterpolation(tmin: float, tmax: float, tdawn: float, tpeak: float):
        return lambda t: (
            (tmax+tmin)/2-(tmax-tmin)/2*cos(pi*(tdawn-t)/(24+tdawn-tpeak)) 
                if t < tdawn else 
            (tmax+tmin)/2+(tmax-tmin)/2*cos(pi*(tpeak-t)/(tpeak-tdawn))
                if t < tpeak else 
            (tmax+tmin)/2-(tmax-tmin)/2*cos(pi*(24+tdawn-t)/(24+tdawn-tpeak)))

    
    def __init__(self, database: SqliteUtil):
        self.database = database

    
    def create_tables(self):
        self.database.drop_table('daymet_centroids')
        self.database.drop_table('daymet_temperatures')
        self.database.cursor.execute('''
            CREATE TABLE daymet_centroids(
                centroid_id MEDIUMINT UNSIGNED,
                temperature_id MEDIUMINT UNSIGNED,
                point VARCHAR(255),
                region TEXT
            );  ''')
        self.database.cursor.execute('''
            CREATE TABLE daymet_temperatures(
                temperature_id MEDIUMINT UNSIGNED,
                temperature_idx TINYINT UNSIGNED,
                time MEDIUMINT UNSIGNED,
                temperature FLOAT
            );  ''')
        self.database.connection.commit()

    
    def create_indexes(self):
        query = '''
            CREATE INDEX daymet_temperatures_temperature
            ON daymet_temperatures(temperature_id, temperature_idx); '''
        self.database.cursor.execute(query)
        query = '''
            CREATE INDEX daymet_centroids_centroid
            ON daymet_centroids(centroid_id); '''
        self.database.cursor.execute(query)
        self.database.connection.commit()


    def ready(self, tmin_files, tmax_files):
        ready = True
        for netcdf_file in tmin_files + tmax_files:
            if not exists(netcdf_file):
                log.warn(f'Could not find file {netcdf_file}.')
                ready = False
        return ready


    def complete(self):
        tables = ('daymet_centroids', 'daymet_temperatures')
        exists = self.database.table_exists(*tables)
        if len(exists):
            present = ', '.join(exists)
            log.info(f'Found tables {present} already in database.')
        return len(exists) > 0

    
    def parse(self, tmin_files, tmax_files, steps, day):
        log.info('Reallocating tables for daymet centroids and temperatures.')
        self.create_tables()

        log.info('Iterating through daymet centroid data.')
        files = zip(tmax_files, tmin_files)
        temperatures = []
        centroids = []
        points = []
        temps = {}
        temperature_id = 0
        centroid_id = 0
        n = 1

        transformer = Transformer.from_crs('epsg:4326', 'epsg:2223', always_xy=True)

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
                            log.info(f'Parsing daymet centroid {centroid_id}.')
                            n <<= 1

            tmaxnc.close()
            tminnc.close()
        
        if centroid_id != n >> 1:
            log.info(f'Parsing daymet centroid {centroid_id}.')

        minx = min(pt[0] for pt in points)
        maxx = max(pt[0] for pt in points)
        miny = min(pt[1] for pt in points)
        maxy = max(pt[1] for pt in points)

        log.info('Calcuating voronoi polygons from centroids.')
        centers = []
        vor = Voronoi(points)
        for centroid, point, region in zip(centroids, vor.points, vor.point_region):
            if -1 not in vor.regions[region]:
                vertices = tuple(vor.vertices[i] for i in vor.regions[region])
                valid = (
                    min(pt[0] for pt in vertices) > minx and
                    max(pt[0] for pt in vertices) < maxx and
                    min(pt[1] for pt in vertices) > miny and
                    max(pt[1] for pt in vertices) < maxy 
                )
                if valid:
                    reg = Polygon(vertices)
                    centers.append(centroid + (dumps(reg.centroid), dumps(reg)))

        log.info('Writing parsed centroids and temperatures to database.')
        self.database.insert_values('daymet_centroids', centers, 4)
        self.database.insert_values('daymet_temperatures', temperatures, 4)
        self.database.connection.commit()

        log.info('Creating indexes on new tables.')
        self.create_indexes()
