
import math

from icarus.util.database import DatabaseHandle
from icarus.util.print import Printer as pr

class AbmValidationDatabase(DatabaseHandle):
    def __init__(self, params=None, database=None):
        super(AbmValidationDatabase, self).__init__(params=params, database=database)
        self.old_db = params['old_db'] if 'old_db' in params else None
        self.new_db = params['new_db'] if 'new_db' in params else None

    def get_count(self, db, tbl):
        query = f'''
            SELECT COUNT(*)
            FROM {db}.{tbl}
        '''
        self.cursor.execute(query)
        return self.cursor.fetchall()[0][0]

    def get_stats(self, db, tbl, col):
        query = f'''
            SELECT
                MIN({col}),
                MAX({col})
            FROM {db}.{tbl}
        '''
        self.cursor.execute(query)
        return self.cursor.fetchall()[0]

    def get_hist(self, db, tbl, col, bin_count=20, bin_size=0):
        limit = f'LIMIT {bin_count}' if bin_size else ''
        if not bin_size:
            low, high = self.get_stats(db, tbl, col)
            bin_size = math.ceil((high - low) / bin_count)
        pr.print(f'Fetching histogram data for {db}.{tbl}.{col}.', time=True)
        query = f'''
            SELECT
                ROUND(({col}) / {bin_size}) * {bin_size} AS bin,
                COUNT(*) as freq
            FROM {db}.{tbl}
            GROUP BY bin
            {limit}
        '''
        self.cursor.execute(query)
        return list(zip(*self.cursor.fetchall()))

    def get_bins(self, db, tbl, col, bin_size=-2):
        query = f'''
            SELECT
                ROUND({col}, {bin_size}) AS bin,
                COUNT(*) AS freq
            FROM {db}.{tbl}
            GROUP BY bin
        '''
        self.cursor.execute(query)
        return list(zip(*self.cursor.fetchall()))

    def get_bins_dif(self, db, tbl, col1, col2, bin_size=-2):
        query = f'''
            SELECT
                ROUND(CAST({col1} AS SIGNED) - CAST({col2} AS SIGNED), 
                    {bin_size}) AS bin,
                COUNT(*) AS freq
            FROM {db}.{tbl}
            GROUP BY bin
        '''
        self.cursor.execute(query)
        return list(zip(*self.cursor.fetchall()))
        
    def get_bins_comp(self, db, tbl, col1, col2, bin_size=-2):
        query = f'''
            SELECT
                bin,
                SUM(freq)
            FROM (
                SELECT
                    ROUND({col1}, {bin_size}) AS bin,
                    COUNT(*) AS freq
                FROM {db}.{tbl}
                GROUP BY bin
                UNION ALL
                SELECT
                    ROUND({col2}, {bin_size}) AS bin,
                    COUNT(*) * -1 AS freq
                FROM {db}.{tbl}
                GROUP BY bin
            ) AS temp
            GROUP BY bin
        '''
        self.cursor.execute(query)
        return list(zip(*self.cursor.fetchall()))

