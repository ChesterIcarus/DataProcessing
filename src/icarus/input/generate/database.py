
from collections import defaultdict

from icarus.util.database import DatabaseUtil

class PlansGeneratorDatabase(DatabaseUtil):
    def get_mazs(self, pts):
        poly = ','.join(f'{pt[0]} {pt[1]}' for pt in pts)
        query = f'''
            SELECT
                mazs.maz
            FROM network.mazs
            WHERE ST_CONTAINS(ST_POLYGONFROMTEXT(
                "POLYGON(({poly}))", 2223),
                mazs.region)
        '''
        self.cursor.execute(query)
        return tuple(row[0] for row in self.cursor.fetchall())

    def get_plans(self, mazs=[], modes=[], sample=1, seed=4321):
        modes = tuple(modes)
        mode = len(modes)
        maz = len(mazs)
        subquery = f'''
            (SELECT
                plans.agent_id,
                plans.plan_size
                {", COUNT(*) AS rtcount" if mode else ""}
            FROM {self.db}.agents AS plans
            {f"""
            INNER JOIN {self.db}.routes AS routes
                ON plans.agent_id = routes.agent_id
                AND routes.mode IN {modes}
            """ if mode else ""}
            {f"""
            WHERE agent_id IN (
                SELECT agent_id
                FROM activities
                WHERE maz IN {mazs})
            """ if maz else ""}
            {"""
            GROUP BY 
                plans.agent_id,
                plans.plan_size
            """ if mode else ""}
            ) AS temp
        '''
        query = f'''
            SELECT
                agent_id,
                plan_size
            FROM {subquery if maz or mode else f"{self.db}.agents"}
            {"WHERE" if mode or sample < 1 else ""}
            {"plan_size DIV 2 = temp.rtcount" if mode else ""}
            {"AND" if mode and sample < 1 else ""}
            {f"RAND({seed}) <= {sample}" if sample < 1 else ""}
            ORDER BY agent_id
        '''
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def get_activities(self, agents=[]):
        agent = len(agents)
        query = f'''
            SELECT
                acts.agent_id,
                acts.agent_idx,
                acts.start_time,
                acts.end_time,
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
            {f"WHERE acts.agent_id IN {agents}" if agent else ""}
        '''
        self.cursor.execute(query)
        activities = defaultdict(list)
        for act in self.cursor.fetchall():
            activities[act[0]].append(act)
        for agent in activities:
            activities[agent].sort(key=lambda a: a[1])
        return activities

    def get_routes(self, agents= []):
        agent = len(agents)
        query = f'''
            SELECT
                agent_id,
                agent_idx,
                mode,
                dur_time
            FROM {self.db}.routes
            {f"WHERE agent_id IN {agents}" if agent else ""}
        '''
        self.cursor.execute(query)
        routes = defaultdict(list)
        for route in self.cursor.fetchall():
            routes[route[0]].append(route)
        for agent in routes:
            routes[agent].sort(key=lambda a: a[1])
        return routes