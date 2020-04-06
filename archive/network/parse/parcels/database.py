
from  icarus.util.database import DatabaseUtil

class ParcelDatabse(DatabaseUtil):
    def create_temp(self):
        self.tables['temp_residences'] = self.tables['residences']
        del self.tables['temp_residences']['spatial_idxs']
        self.tables['temp_commerces'] = self.tables['commerces']
        del self.tables['temp_commerces']['spatial_idxs']

    def count_parcels(self):
        query = f'''
            SELECT COUNT(*)
            FROM {self.db}.apn
        '''
        self.cursor.execute(query)
        result = self.cursor.fetchall()
        return result[0][0]
        
    def write_residences(self, parcels):
        query = f'''
            INSERT INTO {self.db}.temp_residences
            VALUES(
                %s, %s, NULL,
                ST_CENTROID(ST_GEOMETRYFROMTEXT(%s, 2223)),
                ST_GEOMETRYFROMTEXT(%s, 2223))
            '''
        self.cursor.executemany(query, parcels)
        self.connection.commit()

    def write_commerces(self, parcels):
        query = f'''
            INSERT INTO {self.db}.temp_commerces
            VALUES(
                %s, %s, NULL,
                ST_CENTROID(ST_GEOMETRYFROMTEXT(%s, 2223)),
                ST_GEOMETRYFROMTEXT(%s, 2223))
            '''
        self.cursor.executemany(query, parcels)
        self.connection.commit()

    def join_residences(self):
        query = f'''
            CREATE TABLE {self.db}.residences AS
            SELECT
                rp.residence_id AS residence_id,
                rp.apn AS apn,
                mazs.maz AS maz,
                rp.center AS center,
                rp.region AS region
            FROM {self.db}.temp_residences AS rp
            INNER JOIN {self.db}.mazs AS mazs
            ON ST_CONTAINS(mazs.region, rp.center)
        '''
        self.cursor.execute(query)
        self.connection.commit()

    def join_commerces(self):
        query = f'''
            CREATE TABLE commerces AS
            SELECT
                cp.commerce_id AS commerce_id,
                cp.apn AS apn,
                mazs.maz AS maz,
                cp.center AS center,
                cp.region AS region
            FROM temp_commerces AS cp
            INNER JOIN mazs AS mazs
            ON ST_CONTAINS(mazs.region, cp.center)
        '''
        self.cursor.execute(query)
        self.connection.commit()
