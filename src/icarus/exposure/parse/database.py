
from icarus.util.database import DatabaseUtil

class DaymetParserDatabaseHandle(DatabaseUtil):
    def write_centroids(self, centroids):
        query = f'''
            INSERT INTO {self.db}.centroids
                VALUES ( %s, %s,
                    ST_POLYFROMTEXT(%s, 2223),
                    ST_POINTFROMTEXT(%s, 2223)) '''
        self.cursor.executemany(query, centroids)
        self.connection.commit()