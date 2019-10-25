 
from icarus.util.database import DatabaseHandle

class HouseholdsParserDatabase(DatabaseHandle):
    def write_households(self, households):
        self.write_rows(households, 'households')

    def write_vehicles(self, vehicles):
        self.write_rows(vehicles, 'vehicles')
