
from icarus.util.database import DatabaseUtil

class AgentsParserDatabase(DatabaseUtil):
    def write_agents(self, agents):
        self.write_rows(agents, 'agents')