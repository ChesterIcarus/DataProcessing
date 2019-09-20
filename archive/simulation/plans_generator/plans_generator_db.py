
from  icarus.util.database import DatabaseHandle

class PlansGeneratorDatabaseHandle(DatabaseHandle):
    def fetch_mazs(self, pts):
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

    def fetch_plans(self, mazs=[], modes=[], sample=1):
        mode = len(modes)
        maz = len(mazs)
        subquery = f'''
            (SELECT
                plans.agent_id,
                plans.size AS size
                {", COUNT(*) AS rtcount" if mode else ""}
            FROM {self.db}.plans AS plans
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
                plans.size
            """ if mode else ""}
            ) AS temp
        '''
        query = f'''
            SELECT
                agent_id,
                size
            FROM {subquery if maz or mode else f"{self.db}.plans"}
            {"WHERE size div 2 = temp.rtcount" if mode else ""}
            {f"WHERE RAND() >= {sample}" if sample < 1 else ""}
            ORDER BY agent_id
        '''
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def fetch_activities(self, agents=[]):
        agent = len(agents)
        query = f'''
            SELECT
                acts.agent_id,
                acts.agent_index,
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
            ) AS parcels
            USING (apn)
            {f"WHERE acts.agent_id IN {agents}" if agent else ""}
            ORDER BY agent_id, agent_index
        '''
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def fetch_routes(self, agents= []):
        agent = len(agents)
        query = f'''
            SELECT
                agent_id,
                agent_index,
                mode,
                dur_time
            FROM routes
            {f"WHERE agent_id IN {agents}" if agent else ""}
            ORDER BY agent_id, agent_index
        '''
        self.cursor.execute(query)
        return self.cursor.fetchall()