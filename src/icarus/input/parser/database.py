
from collections import defaultdict

from icarus.util.database import DatabaseHandle

class PlansParserDatabase(DatabaseHandle):
    def __init__(self, params=None, database=None):
        super().__init__(database=database, params=params)
        self.abm_db = params['abm_db'] if 'abm_db' in params else ''

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


    def get_trips(self, min_hh, max_hh):
        query = f'''
            SELECT
                trips.trip_id,
                trips.household_id,
                agents.household_idx,
                trips.agent_id,
                trips.agent_idx,
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
            FROM {self.abm_db}.trips AS trips
            LEFT JOIN {self.abm_db}.agents AS agents
            USING (agent_id)
            LEFT JOIN {self.abm_db}.vehicles AS vehicles
            ON trips.household_id = vehicles.household_id
            AND trips.vehicle_id = vehicles.household_idx
            WHERE trips.household_id >= {min_hh}
            AND trips.household_id < {max_hh}
            ORDER BY 
                household_id,
                household_idx '''
        
        self.cursor.execute(query)
        trips = defaultdict(lambda: defaultdict(list))
        for trip in self.cursor.fetchall():
            trips[trip[1]][trip[2]].append(trip)
        return trips


    def write_agents(self, agents):
        self.write_rows(agents, 'agents')

    def write_activities(self, activities):
        self.write_rows(activities, 'activities')

    def write_routes(self, routes):
        self.write_rows(routes, 'routes')
        