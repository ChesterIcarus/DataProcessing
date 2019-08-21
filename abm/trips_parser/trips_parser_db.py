
from util.db_util import DatabaseHandle

class TripsParserDatabaseHandle(DatabaseHandle):
    def fetch_agents(self):
        query = f'''
            SELECT
                household_id,
                agent_index,
                agent_id
            FROM {self.db}.agents
        '''
        self.cursor.execute(query)
        result = self.cursor.fetchall()
        return {f'{row[0]}-{row[1]}':row[2] for row in result}

    def trips_info(self):
        query = f'''
            SELECT
                MAX(trip_id),
                MAX(household_id)
            FROM {self.db}.trips
        '''
        self.cursor.execute(query)
        result = self.cursor.fetchall()
        return result[0] 

    def push_trips(self, trips):
        self.write_rows(trips, 'trips')

    def push_routes(self, routes):
        self.write_rows(routes, 'routes')