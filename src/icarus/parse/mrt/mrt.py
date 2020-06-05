
import re
import csv
import subprocess
import logging as log
from typing import List
from pyproj import Transformer
from shapely.geometry import Point
from shapely.wkt import dumps

from icarus.util.sqlite import SqliteUtil


def hhmm_to_secs(hhmm):
    hrs, mins, ampm = hhmm.upper().replace(' ', ':').split(':')
    return int(hrs) * 3600 + int(mins) * 60 + (ampm == 'PM') * 43200 


class Mrt:
    def __init__(self, database: SqliteUtil):
        self.database = database


    def ready(self):
        return True


    def complete(self):
        return False

    
    def create_tables(self):
        query = '''
            CREATE TABLE mrt_centroids (
                centroid_id INT SIGNED,
                point VARCHAR(255)
            );
        '''
        self.database.cursor.execute(query)
        query = '''
            CREATE TABLE mrt_exposure (
                centroid_id INT UNSIGNED,
                time MEDIUMINT UNSIGNED,
                mrt FLOAT,
                pet FLOAT,
                utci FLOAT
            );
        '''
        self.database.cursor.execute(query)
        self.database.connection.commit()


    def find_files(self, dirpath: str) -> List[str]:
        result = subprocess.run(('find', dirpath, '-name', '*.csv'), capture_output=True)
        files = result.stdout.decode('utf-8').splitlines()
        return files

    
    def parse(self, dirpath: str):
        
        filepaths = self.find_files(dirpath)

        transformer = Transformer.from_crs('epsg:4326', 'epsg:2223', always_xy=True)

        for idx, filepath in enumerate(filepaths):
            log.info(f'Parsing points from {filepath}.')

            with open(filepath, 'r') as mrtfile:
                count, n = 0, 1
                data = []
                points = csv.reader(mrtfile, delimiter=',', quotechar='"')
                next(points)

                for lat, lon, time, mrt, pet, utci in points:
                    point = Point(transformer.transform(lon, lat))
                    secs = hhmm_to_secs(time)
                    data.append((
                        count, 
                        secs, 
                        float(mrt), 
                        float(pet), 
                        float(utci), 
                        dumps(point)))

                    count += 1
                    if count == n:
                        log.info(f'Parsed point {count}.')
                        n <<= 1

            if count != n >> 1:
                log.info(f'Parsed point {count}.')
            
            if idx == 0:
                self.database.insert_values('mrt_dentroids', )

            breakpoint()




                    
        
