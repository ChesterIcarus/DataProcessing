
from  icarus.util.database import DatabaseHandle

class PlansCharterDatabaseHandle(DatabaseHandle):
    def fetch_plans(self, agents):
        query = f'''
            SELECT
                agent_id,
                agent_index,
                dur_time
            FROM {self.db}.routes
            WHERE agent_id IN {agents}
        '''
        self.cursor.execute(query)
        return self.cursor.fetchall()