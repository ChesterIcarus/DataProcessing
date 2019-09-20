
from  icarus.util.database import DatabaseHandle

class MazParserDatabaseHandle(DatabaseHandle):
    def push_mazs(self, mazs):
        self.write_geom_rows(mazs, 'mazs', geo=1)