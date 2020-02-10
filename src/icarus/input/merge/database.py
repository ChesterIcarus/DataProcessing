
from icarus.util.database import DatabaseUtil

class PlansMergerDatabase(DatabaseUtil):

    def get_max(self, db, tbl, col):
        query = f'''
            SELECT MAX({col})
            FROM {db}.{tbl}
        '''
        self.cursor.execute(query)
        return self.cursor.fetchall()[0][0]


    def get_routes(self, agents=[]):
        agents = tuple(agents)
        agent = len(agents)
        query = f'''
            SELECT
                routes.agent_id,
                routes.agent_idx,
                routes.mode,
                routes.start,
                routes.duration,
                routes.vehicle
            FROM {self.db}.routes
            {f"WHERE agent_id IN {agents}" if agent else ""}
            ORDER BY agent_id, agent_idx
        '''
        self.cursor.execute(query)
        return self.cursor.fetchall()

    
    def get_activities(self, agents=[]):
        agents = tuple(agents)
        agent = len(agents)
        query = f'''
            SELECT
                agent_id,
                agent_idx,
                start,
                end
            FROM {self.db}.activities
            {f"WHERE agent_id IN {agents}" if agent else ""}
            ORDER BY agent_id, agent_idx
        '''
        self.cursor.execute(query)
        return self.cursor.fetchall()