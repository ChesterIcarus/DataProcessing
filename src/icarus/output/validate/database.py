
from icarus.util.database import DatabaseUtil

class ValidationDatabaseUtil(DatabaseUtil):
    def setup(self, input_db, output_db):
        self.input_db = input_db
        self.output_db = output_db

    def agent_act_diffs(self):
        query = f'''
            SELECT
                outacts.start - inacts.start,
                outacts.end - inacts.end,
                outacts.duration - inacts.duartion
            FROM {self.output_db}.activities AS inacts
            INNER JOIN {self.input_db}.activities AS outacts
            USING(agent_id, agent_idx) '''
        self.cursor.execute(query)
        return self.connection.fetchall()


    def agent_route_diffs(self):
        query = f'''
            SELECT
                outroutes.start - inroutes.start,
                outroutes.end - inroutes.end,
                outroutes.duration - inroutes.duartion
            FROM {self.output_db}.routes AS inroutes
            INNER JOIN {self.input_db}.routes AS outroutes
            USING(agent_id, agent_idx) '''
        self.cursor.execute(query)
        return self.connection.fetchall()




