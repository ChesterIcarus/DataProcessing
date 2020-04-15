
from collections import defaultdict

from icarus.util.database import DatabaseUtil

class OutputEventsParserDatabaseUtil(DatabaseUtil):
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


    def load_agents(self, filepath):
        query = f'''
            LOAD DATA INFILE '{filepath}' INTO TABLE {self.db}.agents
                FIELDS 
                    TERMINATED BY ',' 
                    ESCAPED BY '\\\\' 
                    OPTIONALLY ENCLOSED BY '"'
                LINES TERMINATED BY '\r\n'
                IGNORE 1 LINES
                ( @agent_id, @size, @exposure )
            SET
                agent_id = @agent_id,
                size = @size,
                exposure = @exposure '''

        self.cursor.execute(query)
        self.connection.commit()


    def load_routes(self, filepath):
        query = f'''
            LOAD DATA INFILE '{filepath}' INTO TABLE {self.db}.routes
                FIELDS 
                    TERMINATED BY ',' 
                    ESCAPED BY '\\\\' 
                    OPTIONALLY ENCLOSED BY '"'
                LINES TERMINATED BY '\r\n'
                IGNORE 1 LINES
                ( @agent_id, @agent_idx, @mode, @start, @end, @duration, @exposure )
            SET
                agent_id = @agent_id,
                agent_idx = @agent_idx,
                mode = @mode,
                `start` = nullif(@start, ''),
                `end` = nullif(@end, ''),
                `duration` = nullif(@duration, ''),
                exposure = nullif(@exposure, '') '''

        self.cursor.execute(query)
        self.connection.commit()

    
    def load_activities(self, filepath):
        query = f'''
            LOAD DATA INFILE '{filepath}' INTO TABLE {self.db}.activities
                FIELDS 
                    TERMINATED BY ',' 
                    ESCAPED BY '\\\\' 
                    OPTIONALLY ENCLOSED BY '"'
                LINES TERMINATED BY '\r\n'
                IGNORE 1 LINES
                ( @agent_id, @agent_idx, @type, @start, @end, @duration, @exposure )
            SET
                agent_id = @agent_id,
                agent_idx = @agent_idx,
                type = @type,
                `start` = nullif(@start, ''),
                `end` = nullif(@end, ''),
                `duration` = nullif(@duration, ''),
                exposure = nullif(@exposure, '') '''

        self.cursor.execute(query)
        self.connection.commit()