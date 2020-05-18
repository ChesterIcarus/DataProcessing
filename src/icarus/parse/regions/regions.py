
import shapefile
import logging as log

from shapely.geometry import Polygon
from shapely.wkt import dumps


class Regions:                
    def __init__(self, database):
        self.database = database


    def create_tables(self):
        query = '''
            CREATE TABLE regions(
                maz SMALLINT UNSIGNED,
                taz SMALLINT UNSIGNED,
                area FLOAT,
                center VARCHAR(255),
                region TEXT
            );  '''
        self.database.cursor.execute(query)
        self.database.connection.commit()

    
    def create_indexes(self):
        query = '''
            CREATE INDEX regions_maz
            ON regions(maz); '''
        self.database.cursor.execute(query)
        self.database.connection.commit()

    
    def ready(self):
        return True

    
    def complete(self):
        tables = ('regions',)
        exists = self.database.table_exists(*tables)
        if len(exists):
            present = ', '.join(exists)
            log.info(f'Found tables {present} already in database.')
        return len(exists) > 0
    

    def parse(self, filepath):
        log.info('Reallocating tables for regions.')
        self.create_tables()

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
                log.info(f'Parsing region {count}.')
                n <<= 1

        if count != n >> 1:
                log.info(f'Parsing region {count}.')
        
        log.info('Writing parsed regions to database.')
        self.database.insert_values('regions', regions, 5)
        self.database.connection.commit()

        log.info('Creating indexes on new tables.')
        self.create_indexes()
