
from collections import defaultdict

from icarus.util.database import DatabaseUtil

class ExposureLinkAnalysisDatabase(DatabaseUtil):
    def fetch_temperatures(self, db):
        query = f'''
            SELECT
                temperature_id,
                temperature_idx,
                temperature
            FROM {db}.temperatures
            ORDER BY
                temperature_id,
                temperature_idx '''
        self.cursor.execute(query)
        temperatures = defaultdict(list)
        for temp in self.cursor.fetchall():
            temperatures[temp[0]].append(temp[2])

        return temperatures

    
    def fetch_links(self, db):
        query = f'''
            SELECT
                links.link_id,
                centroids.temperature_id
            FROM {db}.links AS links
            INNER JOIN {db}.nodes AS nodes
            ON links.source_node = nodes.node_id
            INNER JOIN {db}.centroids AS centroids
            ON ST_CONTAINS(centroids.region, nodes.pt) '''
        self.cursor.execute(query)
        links = {}
        for link in self.cursor.fetchall():
            links[link[0]] = link[1]

        return links


    def fetch_agents(self, db):
        query = f'''
            SELECT
                agent_id,
                plan_size
            FROM {db}.agents '''
        self.cursor.execute(query)
        agents = {}
        for agent in self.cursor.fetchall():
            # { agent_id: [plans: list, vehicle: str, time:int] }
            agents[agent[0]] = [[0]*agent[1], 0, 14400, None]

        return agents


    def fetch_plans(self, db):
        query = f'''
            SELECT
                
        '''

        plans = {}

        return plans

    
    def fetch_parcels(self, db):
        query = f'''

        '''

        parcels = {}

        return parcels


