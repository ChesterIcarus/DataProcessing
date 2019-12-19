 
from icarus.util.database import DatabaseUtil

class HouseholdsParserDatabase(DatabaseUtil):
    def write_households(self, households):
        self.write_rows(households, 'households')

    def write_vehicles(self, vehicles):
        self.write_rows(vehicles, 'vehicles')
