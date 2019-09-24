
from icarus.util.database import DatabaseHandle

class AgentsParserDatabase(DatabaseHandle):
    def write_agents(self, agents):
        self.write_rows(agents, 'agents')