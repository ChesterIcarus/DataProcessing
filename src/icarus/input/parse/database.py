
from collections import defaultdict

from icarus.util.database import DatabaseUtil

class PlansParserDatabase(DatabaseUtil):
    def get_max(self, db, tbl, col):
        query = f'''
            SELECT MAX({col})
            FROM {db}.{tbl}
        '''
        self.cursor.execute(query)
        return self.cursor.fetchall()[0][0]


    def get_parcels(self, table, seed=None):
        if seed is None:
            seed = ''
        query = f'''
            SELECT
                maz,
                apn
            FROM network.{table}
            ORDER BY
                maz,
                RAND({seed})
        '''
        self.cursor.execute(query)
        result = self.cursor.fetchall()
        parcels = {}
        maz = []
        last_maz = 0
        for row in result:
            if row[0] != last_maz and len(maz):
                parcels[last_maz] = maz
                maz = []    
            maz.append(row[1])
            last_maz = row[0]
        return parcels


    def get_trips(self, db, low, high):
        query = f'''
            SELECT
                trips.trip_id,
                trips.household_id,
                agents.household_idx,
                trips.agent_id,
                trips.agent_idx,
                trips.party_id,
                trips.party_idx,
                trips.party_role,
                trips.origin_taz,
                trips.origin_maz,
                trips.dest_taz,
                trips.dest_maz,
                trips.origin_act,
                trips.dest_act,
                trips.mode,
                IFNULL(vehicles.vehicle_id, 0),
                trips.depart_time,
                trips.arrive_time,
                trips.act_duration
            FROM {db}.trips AS trips
            LEFT JOIN {db}.agents AS agents
            USING (agent_id)
            LEFT JOIN {db}.vehicles AS vehicles
            ON trips.household_id = vehicles.household_id
            AND trips.vehicle_id = vehicles.household_idx
            WHERE trips.household_id >= {low}
            AND trips.household_id < {high}
            ORDER BY 
                household_id,
                household_idx '''
        
        self.cursor.execute(query)
        return self.cursor.fetchall()


    def write_agents(self, agents):
        self.write_rows(agents, 'agents')

    def write_activities(self, activities):
        self.write_rows(activities, 'activities')

    def write_routes(self, routes):
        self.write_rows(routes, 'routes')

    def write_households(self, households):
        self.write_rows(households, 'households')
        