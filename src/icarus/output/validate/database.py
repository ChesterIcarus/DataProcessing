
from  icarus.util.database import DatabaseHandle

class ValidationDatabase(DatabaseHandle):
    def __init__(self, params=None, database=None, config=None):
        super().__init__(params=params, database=database)
        self.input_db = config['input_db']
        self.output_db = config['output_db']

    def count(self, db, tbl):
        query = f'''
            SELECT COUNT(*)
            FROM {db}.{tbl}
        '''
        self.cursor.execute(query)
        return self.cursor.fetchall()[0][0]

    def rmse(self, tbl, col):
        query = f'''
            SELECT SQRT(SUM(err) / COUNT(*))
            FROM (
                SELECT
                    POW(
                        CAST(output.{col} AS SIGNED) - 
                        CAST(input.{col} AS SIGNED), 2) AS err
                FROM {self.output_db}.{tbl} AS output
                INNER JOIN {self.input_db}.{tbl} AS input
                USING (agent_id, agent_idx)
            ) AS temp
        '''
        self.cursor.execute(query)
        return float(self.cursor.fetchall()[0][0])

    def rmspe(self, tbl, col):
        query = f'''
            SELECT SQRT(SUM(err) / COUNT(*))
            FROM (
                SELECT
                    POW((
                        CAST(output.{col} AS SIGNED) - 
                        CAST(input.{col} AS SIGNED)) / 
                        CAST(input.{col} AS SIGNED), 2) AS err
                FROM {self.output_db}.{tbl} AS output
                INNER JOIN {self.input_db}.{tbl} AS input
                USING (agent_id, agent_idx)
            ) AS temp
        '''
        self.cursor.execute(query)
        return float(self.cursor.fetchall()[0][0])

    def me(self, tbl, col):
        query = f'''
            SELECT SQRT(SUM(err) / COUNT(*))
            FROM (
                SELECT
                    CAST(output.{col} AS SIGNED) - 
                    CAST(input.{col} AS SIGNED) AS err
                FROM {self.output_db}.{tbl} AS output
                INNER JOIN {self.input_db}.{tbl} AS input
                USING (agent_id, agent_idx)
            ) AS temp
        '''
        self.cursor.execute(query)
        return float(self.cursor.fetchall()[0][0])

    def mpe(self, tbl, col):
        query = f'''
            SELECT SQRT(SUM(err) / COUNT(*))
            FROM (
                SELECT
                    (CAST(output.{col} AS SIGNED) - 
                    CAST(input.{col} AS SIGNED)) /
                    CAST(input.{col} AS SIGNED) AS err
                FROM {self.output_db}.{tbl} AS output
                INNER JOIN {self.input_db}.{tbl} AS input
                USING (agent_id, agent_idx)
            ) AS temp
        '''
        self.cursor.execute(query)
        return float(self.cursor.fetchall()[0][0])  

    def correlation(self, tbl, col):
        query = f'''
            SELECT 
                AVG(output.{col}),
                STDDEV_SAMP(output.{col}),
                AVG(input.{col}),
                STDDEV_SAMP(input.{col})
            FROM {self.output_db}.{tbl} AS output
            INNER JOIN {self.input_db}.{tbl} AS input
            USING (agent_id, agent_idx)
        '''
        self.cursor.execute(query)
        stats =  [float(col) for col in self.cursor.fetchall()[0]]
        query = f'''
            SELECT SUM(err) / (COUNT(*) - 1)
            FROM (
                SELECT
                    (CAST(output.{col} AS SIGNED) - {stats[0]}) *
                    (CAST(input.{col} AS SIGNED) - {stats[2]}) /
                    {stats[1] * stats[3]} AS err
                FROM {self.output_db}.{tbl} AS output
                INNER JOIN {self.input_db}.{tbl} AS input
                USING (agent_id, agent_idx)
            ) AS temp
        '''
        self.cursor.execute(query)
        return float(self.cursor.fetchall()[0][0])


    def coeff(self, tbl, col):
        query = f'''
            SELECT SUM(err)
            FROM (
                SELECT SQRT(SUM(POW(output.{col}, 2)) / COUNT(*)) AS err
                FROM {self.output_db}.{tbl} AS output
                UNION
                SELECT SQRT(SUM(POW(input.{col}, 2)) / COUNT(*)) AS err
                FROM {self.input_db}.{tbl} AS input
            ) AS temp
        '''
        self.cursor.execute(query)
        coeff = self.cursor.fetchall()[0][0]
        return self.rmse(tbl, col) / float(coeff)

    def bias(self, tbl, col):
        query = f'''
            SELECT POW(SUM(err), 2)
            FROM (
                SELECT AVG(output.{col}) AS err
                FROM {self.output_db}.{tbl} AS output
                UNION
                SELECT -AVG(input.{col}) AS err
                FROM {self.input_db}.{tbl} AS input
            ) AS temp
        '''
        self.cursor.execute(query)
        return float(self.cursor.fetchall()[0][0]) / self.rmse(tbl, col) ** 2

    def variance(self, tbl, col):
        query = f'''
            SELECT POW(SUM(err), 2)
            FROM (
                SELECT STDDEV_SAMP(output.{col}) AS err
                FROM {self.output_db}.{tbl} AS output
                UNION
                SELECT -STDDEV_SAMP(input.{col}) AS err
                FROM {self.input_db}.{tbl} AS input
            ) AS temp
        '''
        self.cursor.execute(query)
        return float(self.cursor.fetchall()[0][0]) / self.rmse(tbl, col) ** 2

    def covariance(self, tbl, col):
        query = f'''
            SELECT 
                STDDEV_SAMP(output.{col}),
                STDDEV_SAMP(input.{col})
            FROM {self.output_db}.{tbl} AS output
            INNER JOIN {self.input_db}.{tbl} AS input
            USING (agent_id, agent_idx)
        '''
        self.cursor.execute(query)
        stats =  [float(col) for col in self.cursor.fetchall()[0]]
        return (2 * (1 -  self.correlation(tbl, col)) * stats[0] * stats[1] /
            self.rmse(tbl, col) ** 2)