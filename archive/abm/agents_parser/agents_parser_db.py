
from  icarus.util.database import DatabaseHandle

class AgentsParserDatabaseHandle(DatabaseHandle):
    def count_agents(self):
        query = f'''
            SELECT COUNT(*)
            FROM {self.db}.agents '''
        self.cursor.execute(query)
        return self.cursor.fetchall()[0][0]
        
    def push_agents(self, agents):
        self.write_rows(agents, 'agents')