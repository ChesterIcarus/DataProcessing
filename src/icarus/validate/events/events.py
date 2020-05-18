
import logging as log

from icarus.util.sqlite import SqliteUtil


def perc(prop, digits=2):
    perc = round(prop * 100, digits)
    return f'{perc}%'


class Events:
    def __init__(self, database: SqliteUtil):
        self.database = database

    
    def event_count(self):
        query = '''
            SELECT
                freq,
                COUNT(*)
            FROM (
                SELECT
                    COUNT(*) as freq
                FROM output_legs
                LEFT JOIN output_events
                USING(leg_id)
                WHERE mode IN ("walk", "bike")
                GROUP BY leg_id
            ) AS temp
            GROUP BY freq; '''
        self.database.cursor.execute(query)
        count = self.database.cursor.fetchall()
        total = sum(row[1] for row in count)
        zero = sum(row[1] for row in count if row[0] == 0)

        if zero == 0:
            log.info('All walk and bike legs have event level data.')
        else:
            log.error(f'There are {zero} ({perc(zero/total)}) walk and bike legs'
                ' without event level data; check event parsing for issues.')

        return zero == 0
