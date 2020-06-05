
from pprint import pprint

from icarus.util.general import defaultdict
from icarus.util.sqlite import SqliteUtil



class DemographicsVisualization:
    def __init__(self, database: SqliteUtil):
        self.database = database


    def get_demographics(self):
        query = '''
            SELECT
                persons.age,
                person.personType,
                person.personTypeDetailed,
                person.gender,
                output_agents.exposure
            FROM agents
            INNER JOIN output_agents
            USING(agent_id)
            INNER JOIN persons
            ON hhid = household_id
            AND pnum = household_idx;
        '''
        self.database.cursor.execute(query)
        agents = self.database.cursor.fetchall()

        ages = defaultdict(lambda: (0,0))
        kinds = defaultdict(lambda: (0,0))
        detailedKinds = defaultdict(lambda: (0,0))
        sexs = defaultdict(lambda: (0,0))

        for age, kind, detailedKind, sex, exp in agents:
            ages[age // 10][0] += 1
            ages[age // 10][1] += exp
            kinds[kind][0] += 1
            kinds[kind][1] += exp
            detailedKinds[detailedKind][0] += 1
            detailedKinds[detailedKind][1] += exp
            sexs[sex][0] += 1
            sexs[sex][1] += exp
            
        return ages, kinds, detailedKinds, sexs



    def visualize(self):
        pass
