
from icarus.util.database import DatabaseHandle

class TripsParserDatabase(DatabaseHandle):
    def write_trips(self, trips):
        self.write_rows(trips, 'trips')

    def count_trips(self):
        query = f'''
            SELECT COUNT(*)
            FROM {self.db}.trips
        '''
        self.cursor.execute(query)
        return self.cursor.fetchall()[0][0]
