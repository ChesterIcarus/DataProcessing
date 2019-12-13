
from icarus.util.database import DatabaseHandle

class MazParserDatabase(DatabaseHandle):
    def push_mazs(self, mazs):
        self.write_geom_rows(mazs, 'mazs', geo=1)