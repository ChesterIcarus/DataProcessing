
import shapefile
import logging as log

from shapely.geometry import Polygon
from shapely.wkt import dumps


class Regions:                
    def __init__(self, database):
        self.database = database
    

    def parse(self, filepath):
        'parse maricopa maz/taz regions from source file'

        log.info('Loading Maricopa MAZ and TAZ region data.')
        parser = shapefile.Reader(filepath)
        regions = []
        count = 0
        n = 1

        log.info('Parsing regions from data.')
        for item in parser:
            poly = Polygon(item.shape.points)
            regions.append((
                item.record.MAZ_ID_10,
                item.record.TAZ_2015,
                item.record.Sq_miles,
                dumps(poly.centroid),
                dumps(poly)))

            count += 1
            if count == n:
                log.info(f'Parsed region {count}.')
                n <<= 1
        if count != n >> 1:
                log.info(f'Parsed region {count}.')
        
        log.info('Writing parsed regions to database.')
        self.database.drop_table('regions')
        self.database.cursor.execute(f'''
            CREATE TABLE regions(
                maz SMALLINT UNSIGNED,
                taz SMALLINT UNSIGNED,
                area FLAOT,
                center VARCHAR(255),
                region TEXT
            );  ''')
        self.database.cursor.executemany('INSERT INTO regions VALUES '
            '(?, ?, ?, ?, ?)', regions)
        self.database.connection.commit()


    def validate(self):
        pass