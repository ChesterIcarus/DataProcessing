
from icarus.util.database import DatabaseUtil

class ValidationDatabaseUtil(DatabaseUtil):
    def setup(self, input_db, output_db):
        self.input_db = input_db
        self.output_db = output_db

    def agent_act_diffs(self, parameter, bounds=None, sample=None, acts=None):
        conds = []
        if acts is not None:
            if len(acts) > 1:
                conds.append(f'outacts.type IN {tuple(acts)}')
            else:
                conds.append(f'outacts.type = {acts[0]}')
        if bounds is not None:
            conds.append(f'inacts.{parameter} >= {bounds[0]}')
            conds.append(f'outacts.{parameter} >= {bounds[1]}')
            conds.append(f'inacts.{parameter} <= {bounds[2]}')
            conds.append(f'outacts.{parameter} <= {bounds[3]}')

        condition = 'WHERE ' + ' AND '.join(conds) if len(conds) else ''
        limit = f'LIMIT {sample}' if sample is not None else ''
        
        query = f'''
            SELECT 
                inacts.{parameter},
                outacts.{parameter}
            FROM {self.input_db}.activities AS inacts
            INNER JOIN {self.output_db}.activities AS outacts
            USING(agent_id, agent_idx)
            {condition}
            {limit} '''
            
        self.cursor.execute(query)
        return self.cursor.fetchall()


    def agent_route_diffs(self, parameter, bounds=None, sample=None, modes=None):
        conds = []
        if modes is not None:
            if len(modes) > 1:
                conds.append(f'outroutes.mode IN {tuple(modes)}')
            else:
                conds.append(f'outroutes.mode = "{modes[0]}"')
        if bounds is not None:
            conds.append(f'inroutes.{parameter} >= {bounds[0]}')
            conds.append(f'outroutes.{parameter} >= {bounds[1]}')
            conds.append(f'inroutes.{parameter} <= {bounds[2]}')
            conds.append(f'outroutes.{parameter} <= {bounds[3]}')

        condition = 'WHERE ' + ' AND '.join(conds) if len(conds) else ''
        limit = f'LIMIT {sample}' if sample is not None else ''
        
        query = f'''
            SELECT 
                inroutes.{parameter},
                outroutes.{parameter}
            FROM {self.input_db}.routes AS inroutes
            INNER JOIN {self.output_db}.routes AS outroutes
            USING(agent_id, agent_idx)
            {condition}
            {limit} '''

        self.cursor.execute(query)
        return self.cursor.fetchall()




