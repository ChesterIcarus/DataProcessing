
from collections import defaultdict
from netCDF4 import Dataset
from pyproj import Proj, transform
from math import cos, pi


class DaymetParser:
    def __init__(self):
        pass

    def encode_point(self, x, y):
        return f'ST_GEOMFROMTEXT(POINT({x} {y}), 2223)'

    def iterpolation(self, tmin, tmax, tdawn, tpeak):
        return lambda t: (
            (tmax+tmax)/2-(tmax-tmin)/2*cos(pi*(tdawn-t)/(24+tdawn-tpeak)) if t < tdawn
            else (tmax+tmax)/2+(tmax-tmin)/2*cos(pi*(tpeak-t)/(tpeak-tdawn)) if t < tpeak
            else (tmax+tmax)/2-(tmax-tmin)/2*cos(pi*(24+tdawn-t)/(24+tdawn-tpeak)))
        

    def run(self, config, silent=False):

        day = config['day']
        steps = config['steps']

        centroids = []
        centroid_id = 0
        temperatures = {}
        temperature_id = 0

        srccrs = Proj(init='espg:4326')
        tarcrs = Proj(init='espg:2223')

        tmax = Dataset(config['tmax_file'], 'r')
        tmin = Dataset(config['tmin_file'], 'r')
        
        shape = tmax.variables['tmax'].shape

        for i in range(shape[1]):
            for j in range(shape[2]):
                lon = tmax.variables['lon'][i][j]
                lat = tmax.variables['lat'][i][j]
                point = self.encode_point(*transform(srccrs, tarcrs, lat, lon))
                maxtemp = tmax.variables['tmax'][day][i][j]
                mintemp = tmin.variables['tmin'][day][i][j]
                idx = f'{maxtemp}-{mintemp}'

                if idx not in temperatures:
                    temp = self.iterpolation(mintemp, maxtemp, 5, 15)
                    temperatures[idx] = [(
                        temperature_id,
                        step,
                        int(86400 * idx / steps),
                        temp(24*idx/steps)) for step in range(steps)]
                    temperature_id += 1
                
                centroids.append((centroid_id, temperatures[idx][0], point))
                centroid_id += 1
                
