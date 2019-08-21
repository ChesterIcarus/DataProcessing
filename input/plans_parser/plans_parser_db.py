
from util.db_util import DatabaseHandle

class PlansParserDatabaseHandle(DatabaseHandle):
    def count_trips(self):
        query = f'''
            SELECT MAX(trip_id)
            FROM abm.trips
        '''
        self.cursor.execute(query)
        return self.cursor.fetchall()[0][0] + 1

    def count_households(self):
        query = f'''
            SELECT MAX(household_id)
            FROM abm.trips
        '''
        self.cursor.execute(query)
        return self.cursor.fetchall()[0][0] + 1

    def fetch_parcels(self):
        query = f'''
            SELECT
                maz,
                apn,
                RAND() AS ord
            FROM network.parcels
            ORDER BY
                maz,
                ord
        '''
        self.cursor.execute(query)
        result = self.cursor.fetchall()
        parcels = {}
        maz = []
        last_maz = 1
        for row in result:
            if row[0] != last_maz:
                parcels[last_maz] = maz
                maz = []    
            maz.append(row[1])
            last_maz = row[0]
        return parcels

    def fetch_res_parcels(self):
        query = f'''
            SELECT
                maz,
                apn,
                RAND() as `rand`
            FROM network.residences
            ORDER BY
                maz,
                `rand`
        '''
        self.cursor.execute(query)
        result = self.cursor.fetchall()
        parcels = {}
        maz = []
        last_maz = 1
        for row in result:
            if row[0] != last_maz:
                parcels[last_maz] = maz
                maz = []    
            maz.append(row[1])
            last_maz = row[0]
        return parcels

    def fetch_com_parcels(self):
        query = f'''
            SELECT
                maz,
                apn,
                RAND() as `rand`
            FROM network.commerces
            ORDER BY
                maz,
                `rand`
        '''
        self.cursor.execute(query)
        result = self.cursor.fetchall()
        parcels = {}
        maz = []
        last_maz = 1
        for row in result:
            if row[0] != last_maz:
                parcels[last_maz] = maz
                maz = []    
            maz.append(row[1])
            last_maz = row[0]
        return parcels

    def fetch_trips(self, min_hhid, max_hhid):
        query = f'''
            SELECT
                trip_id,
                household_id,
                household_index,
                agent_id,
                agent_index,
                mode,
                origin_act,
                dest_act,
                origin_maz,
                dest_maz,
                start_time,
                end_time
            FROM abm.trips
            WHERE household_id >= {min_hhid}
            AND household_id < {max_hhid}
            ORDER BY
                trip_id ASC
        '''
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def write_plans(self, plans):
        self.write_rows(plans, 'plans')

    def write_activities(self, activities):
        self.write_rows(activities, 'activities')

    def write_routes(self, routes):
        self.write_rows(routes, 'routes')