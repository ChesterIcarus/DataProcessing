
import re
import csv
import subprocess
import logging as log
from typing import List
from pyproj import Transformer

from icarus.util.sqlite import SqliteUtil
from icarus.util.general import counter


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
        self.database.drop_table('mrt_centroids')
        self.database.drop_table('mrt_temperatures')
        query = '''
            CREATE TABLE mrt_centroids (
                centroid_id INT UNSIGNED,
                point VARCHAR(255),
                region TEXT
            );
        '''
        self.database.cursor.execute(query)
        query = '''
            CREATE TABLE mrt_temperatures (
                centroid_id INT UNSIGNED,
                time MEDIUMINT UNSIGNED,
                mrt FLOAT,
                pet FLOAT,
                utci FLOAT
            );
        '''
        self.database.cursor.execute(query)
        self.database.connection.commit()

    
    def create_indexes(self):
        query = '''
            CREATE INDEX mrt_centroids_centroid
            ON mrt_centroids(centroid_id);
        '''
        self.database.cursor.execute(query)
        query = '''
            CREATE INDEX mrt_temperatures_centroid
            ON mrt_temperatures(centroid_id);
        '''
        self.database.cursor.execute(query)
        self.database.connection.commit()


    def find_files(self, dirpath: str) -> List[str]:
        result = subprocess.run(('find', dirpath, '-name', '*.csv'), 
            capture_output=True)
        files = result.stdout.decode('utf-8').splitlines()
        return files

    
    def parse(self, dirpath: str):

        self.create_tables()
        filepaths = self.find_files(dirpath)
        transformer = Transformer.from_crs('epsg:4326', 'epsg:2223', always_xy=True)

        for idx, filepath in enumerate(filepaths):
            log.info(f'Parsing points from {filepath}.')

            mrtfile = open(filepath, 'r')
            points = csv.reader(mrtfile, delimiter=',', quotechar='"')

            centroids = []
            temperatures = []
            count = 0
            
            next(points)
            points = counter(points, 'Parsing point %s.')

            for lat, lon, time, mrt, pet, utci in points:
                count += 1
                secs = hhmm_to_secs(time)
                temperatures.append((
                    count, 
                    secs, 
                    float(mrt), 
                    float(pet), 
                    float(utci)
                ))
                if idx == 0:
                    x, y = transformer.transform(lon, lat)
                    centroids.append((
                        count,
                        f'POINT ({x} {y})',
                        None
                    ))

            self.database.insert_values('mrt_temperatures', temperatures, 5)
            if idx == 0:
                self.database.insert_values('mrt_centroids', centroids, 2)
            self.database.connection.commit()

        self.create_indexes()
        
