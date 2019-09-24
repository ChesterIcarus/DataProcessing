
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

    def get_parcels(self, db, tbl, seed=''):
        if seed is None:
            seed = ''
        query = f'''
            SELECT
                maz,
                apn
            FROM {db}.{tbl}
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
            SELECT *
            FROM {self.abm_db}.trips
            WHERE household_id >= {min_hh}
            AND household_id < {max_hh}
        '''
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def write_agents(self, agents):
        self.write_rows(agents, 'agents')

    def write_activities(self, activities):
        self.write_rows(activities, 'activities')

    def write_routes(self, routes):
        self.write_rows(routes, 'routes')