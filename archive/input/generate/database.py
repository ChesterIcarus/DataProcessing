
from collections import defaultdict

from icarus.util.database import DatabaseUtil

class PlansGeneratorDatabase(DatabaseUtil):
    def get_size(self, table):
        query = f'''
            SELECT COUNT(*)
            FROM {self.db}.{table}  '''
        self.cursor.execute(query)
        return self.cursor.fetchall()[0][0]
        

    def get_plans(self, modes={}, limit=None, seed=''):
        condition = ' AND '.join(f'uses_{mode} = {int(val)}'
            for mode, val in modes.items() if val is not None)
        condition = f'WHERE {condition}' if len(condition) else ''
        limit = f'LIMIT {limit}' if limit is not None else ''
        query = f'''
            SELECT 
                agent_id,
                size
            FROM {self.db}.agents
            {condition}
            ORDER BY RAND({seed})
            {limit}  '''
        self.cursor.execute(query)
        return self.cursor.fetchall()


    def get_activities(self, agents):
        query = f'''
            SELECT
                acts.agent_id,
                acts.agent_idx,
                acts.start,
                acts.end,
                acts.type,
                ST_X(parcels.center),
                ST_Y(parcels.center)
            FROM {self.db}.activities AS acts
            INNER JOIN (
                SELECT 
                    center,
                    apn
                FROM network.residences
                UNION
                SELECT
                    center,
                    apn
                FROM network.commerces
                UNION
                SELECT
                    center,
                    apn
                FROM network.mazparcels
            ) AS parcels
            USING (apn)
            WHERE acts.agent_id IN {agents} '''
        self.cursor.execute(query)
        activities = defaultdict(list)
        for act in self.cursor.fetchall():
            activities[act[0]].append(act)
        for agent in activities:
            activities[agent].sort(key=lambda a: a[1])
        return activities


    def get_routes(self, agents):
        query = f'''
            SELECT
                agent_id,
                agent_idx,
                mode,
                duration
            FROM {self.db}.routes
            WHERE agent_id IN {agents}  '''
        self.cursor.execute(query)
        routes = defaultdict(list)
        for route in self.cursor.fetchall():
            routes[route[0]].append(route)
        for agent in routes:
            routes[agent].sort(key=lambda a: a[1])
        return routes
