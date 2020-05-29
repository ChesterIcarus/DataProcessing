
import shapefile
import logging as log
from shapely.geometry import Point, Polygon
from shapely.strtree import STRtree
from shapely.wkt import loads, dumps

from icarus.util.file import exists


class Parcels:
    def __init__(self, database):
        self.database = database

    
    def create_tables(self):
        self.database.drop_table('parcels')
        query = '''
            CREATE TABLE parcels(
                apn VARCHAR(255),
                maz SMALLINT UNSIGNED,
                type VARCHAR(255),
                center VARCHAR(255),
                region TEXT
            );  '''
        self.database.cursor.execute(query)
        self.database.connection.commit()

    
    def create_indexes(self):
        query = '''
            CREATE INDEX parcels_apn
            ON parcels(apn); '''
        self.database.cursor.execute(query)
        query = '''
            CREATE INDEX parcels_maz
            ON parcels(maz); '''
        self.database.cursor.execute(query)
        self.database.connection.commit()

    
    def ready(self, residence_file, commerce_file, parcel_file):
        ready = True
        tables = ('regions',)
        present = self.database.table_exists(*tables)
        if len(exists) < len(tables):
            missing = ', '.join(set(tables) - set(present))
            log.info(f'Could not find tables {missing} in database.')
            ready = False
        parcel_files = (residence_file, commerce_file, parcel_file)
        for parcel_file in parcel_files:
            if not exists(parcel_file):
                log.warn(f'Could not find file {parcel_file}.')
                ready = False
        return ready


    def complete(self):
        tables = ('parcels',)
        exists = self.database.table_exists(*tables)
        if len(exists):
            present = ', '.join(exists)
            log.info(f'Found tables {present} already in database.')
        return len(exists) > 0
    
    
    def parse(self, residence_file, commerce_file, parcel_file):
        mazs = {}
        parcel_polygons = {}
        maz_polygons = []
        parcels = []

        log.info('Reallocating tables for parcels.')
        self.create_tables()

        log.info('Loading region code data.')
        self.database.cursor.execute('SELECT maz, region FROM regions;')
        regions = self.database.cursor.fetchall()

        log.info('Constructing strtree spatial index.')
        for maz, boundary in regions:
            polygon = Polygon(loads(boundary))
            mazs[id(polygon)] = maz
            maz_polygons.append(polygon)
        tree = STRtree(maz_polygons)

        log.info('Parsing parcel boudaries from shapefile.')
        count = 0
        n = 1
        parser = shapefile.Reader(parcel_file)
        for parcel in parser:
            if len(parcel.shape.points):
                apn = parcel.record['APN']
                polygon = Polygon(parcel.shape.points)
                maz = next((mazs[id(region)] for region 
                    in tree.query(polygon.centroid)
                    if region.buffer(0.00001).contains(polygon.centroid)), None)
                if maz is not None:
                    parcel_polygons[apn] = (maz, polygon)
                    count += 1
                    if count == n:
                        log.info(f'Parsing boundary {count}.')
                        n <<= 1
        if count != n >> 1:
            log.info(f'Parsing boundary {count}.')
        
        log.info('Parsing residential parcels from database file.')
        count = 0
        n = 1
        parser = shapefile.Reader(residence_file)
        for record in parser.iterRecords():
            apn = record['APN']
            if apn in parcel_polygons:
                parcels.append((
                    apn,
                    parcel_polygons[apn][0],
                    'residential',
                    dumps(parcel_polygons[apn][1].centroid),
                    dumps(parcel_polygons[apn][1])))
                count += 1
                if count == n:
                    log.info(f'Parsing residential parcel {count}.')
                    n <<= 1
                del parcel_polygons[apn]
        if count != n >> 1:
            log.info(f'Parsing residential parcel {count}.')

        log.info('Parsing commercial parcels from database file.')
        count = 0
        n = 1
        parser = shapefile.Reader(commerce_file)
        for record in parser.iterRecords():
            apn = record['APN']
            if apn in parcel_polygons:
                parcels.append((
                    apn,
                    parcel_polygons[apn][0],
                    'commercial',
                    dumps(parcel_polygons[apn][1].centroid),
                    dumps(parcel_polygons[apn][1])))
                count += 1
                if count == n:
                    log.info(f'Parsing commercial parcel {count}.')
                    n <<=1
                del parcel_polygons[apn]
        if count != n >> 1:
            log.info(f'Parsing commercial parcel {count}.')

        log.info('Adding extraneous and default parcels.')
        for apn, polygon in parcel_polygons.items():
            parcels.append((
                apn,
                polygon[0],
                'other',
                dumps(polygon[1].centroid),
                dumps(polygon[1])))

        for polygon in maz_polygons:
            maz = mazs[id(polygon)]
            parcels.append((
                f'maz-{maz}',
                maz,
                'default',
                dumps(polygon.centroid),
                dumps(polygon)))
        
        log.info('Writing parsed parcels to database.')
        self.database.insert_values('parcels', parcels, 5)
        self.database.connection.commit()

