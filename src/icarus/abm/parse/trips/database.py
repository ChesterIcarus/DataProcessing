
from icarus.util.database import DatabaseHandle

class TripsParserDatabase(DatabaseHandle):
    def create_temp(self):
        self.tables['temp_trips'] = {}
        self.tables['temp_trips']['schema'] = self.tables['trips']['schema']
        self.tables['temp_trips']['btree_idxs'] = {
            'households': [
                'household_id',
                'agent_id'
            ]
        }
        self.create_table('temp_trips')

    def write_trips(self, trips):
        self.write_rows(trips, 'temp_trips')

    def count_trips(self):
        query = f'''
            SELECT COUNT(*)
            FROM {self.db}.trips
        '''
        self.cursor.execute(query)
        return self.cursor.fetchall()[0][0]

    def join_trips(self):
        cols = [col.split(' ')[0] for col in self.tables['trips']['schema']]
        cols = [f'temp.{col}' if col != 'agent_id' else f'agents.{col}'
            for col in cols]
        query = f'''
            CREATE TABLE {self.db}.trips
            SELECT
                {", ".join(cols)}
            FROM {self.db}.temp_trips AS temp
            INNER JOIN {self.db}.agents AS agents
            ON temp.household_id = agents.household_id
            AND temp.agent_id = agents.household_idx
        '''
        self.cursor.execute(query)
        self.connection.commit()
