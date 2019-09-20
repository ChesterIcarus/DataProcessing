
from  icarus.util.database import DatabaseHandle

class PlansComparatorDatbaseHandle(DatabaseHandle):
    def get_trips(self, agents):
        query = f'''
            SELECT
                agent_id,
                agent_index,
                dur_time
            FROM {self.db}.routes
            WHERE agent_id IN {agents} 
        '''
        self.cursor.execute(query)
        result = self.cursor.fetchall()
        return {f'{row[0]}-{row[1]}': row[2] for row in result}
