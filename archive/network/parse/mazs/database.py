
from icarus.util.database import DatabaseUtil

class MazParserDatabase(DatabaseUtil):
    def push_mazs(self, mazs):
        self.write_geom_rows(mazs, 'mazs', geo=1)