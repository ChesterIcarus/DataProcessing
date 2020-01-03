
from  icarus.util.database import DatabaseUtil

class RoadParserDatabase(DatabaseUtil):
    def write_nodes(self, nodes):
        query = f'''
            INSERT INTO {self.db}.nodes
                VALUES (
                    %s,
                    ST_POINTFROMTEXT(%s, 2223)) '''
        self.cursor.executemany(query, nodes)
        self.connection.commit()

    
    def write_links(self, links):
        self.write_rows(links, 'links')