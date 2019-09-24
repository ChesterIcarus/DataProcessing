 
from icarus.util.database import DatabaseHandle

class HouseholdsParserDatabase(DatabaseHandle):
    def write_households(self, households):
        self.write_rows(households, 'households')
