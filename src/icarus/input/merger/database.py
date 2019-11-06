
from icarus.util.database import DatabaseHandle

class PlansMergerDatabase(DatabaseHandle):

    def get_routes(self, agents=[]):
        agent = len(agents)
        query = f'''
            SELECT
                routes.agent_id,
                routes.agent_idx,
                routes.mode,
                routes.start_time,
                routes.dur_time,
                routes.vehicle_id
            FROM {self.db}.routes
            {f"WHERE agent_id IN {agents}" if agent else ""}
            ORDER BY agent_id, agent_idx
        '''
        self.cursor.execute(query)
        return self.cursor.fetchall()

    
    def get_activities(self, agents=[]):
        agent = len(agents)
        query = f'''
            SELECT
                agents_id,
                agent_idx,
                start_time,
                end_time
            FROM {self.db}.activities
            {f"WHERE agent_id IN {agents}" if agent else ""}
            ORDER BY agent_id, agent_idx
        '''
        self.cursor.execute(query)
        return self.cursor.fetchall()