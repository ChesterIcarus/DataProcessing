
import logging as log
from xml.etree.ElementTree import iterparse
from icarus.output.objects.network import Network
from icarus.output.objects.population import Population
from icarus.util.file import multiopen
from icarus.util.general import defaultdict


def hhmmss(secs):
    hh = secs // 3600
    secs -= hh * 3600
    mm = secs // 60
    secs -= mm * 60
    ss = secs
    return f'{str(hh).zfill(2)}:{str(mm).zfill(2)}:{str(ss).zfill(2)}'



class Parsing:
    def __init__(self, database):
        self.database = database

    def create_tables(self):
        self.database.drop_table('output_agents', 'output_activities', 'output_legs')
        self.database.cursor.execute('''
            CREATE TABLE output_agents (
                agent_id MEDIUMINT UNSIGNED,
                plan_size TINYINT UNSIGNED,
                exposure FLOAT
            );  ''')
        self.database.cursor.execute('''
            CREATE TABLE output_activities (
                agent_id MEDIUMINT UNSIGNED,
                agent_idx TINYINT UNSINGED,
                type VARCHAR(255),
                start MEDIUMINT UNISGNED,
                end MEDIUMINT UNSIGNED,
                duration MEDIUMINT UNSIGNED,
                exposure FLOAT
            );  ''')
        self.database.cursor.execute('''
            CREATE TABLE output_legs (
                agent_id MEDIUMINT UNSIGNED,
                agent_idx MEDIUMINT UNSIGNED,
                mode VARCHAR(255),
                start MEDIUMINT UNISGNED,
                end MEDIUMINT UNSIGNED,
                duration MEDIUMINT UNSIGNED,
                exposure FLOAT
            );  ''')

    
    def create_indexes(self):
        self.database.cursor.execute('''
            CREATE INDEX output_agents_agent
            ON output_agents(agent_id); ''')
        self.database.cursor.execute('''
            CREATE INDEX output_activities_agent
            ON output_activities(agent_id, agent_idx); ''')
        self.database.cursor.execute('''
            CREATE INDEX output_legs_agent
            ON output_legs(agent_id, agent_idx); ''')

    
    def complete(self):
        tables = ('output_agents', 'output_activities', 'output_legs')
        return len(self.database.table_exists(*tables)) == len(tables)


    def parse(self, planspath, eventspath):
        eventsfile = multiopen(eventspath, mode='rb')
        events = iter(iterparse(eventsfile, events=('start', 'end')))
        evt, root = next(events)

        log.info('Loading and building network for exposure analysis.')
        network = Network(self.database)
        network.load_network(planspath)
        population = Population(network)

        count = 0
        time = 14400
        n = 14400

        log.info('Iterating over events file and calculating exposure.')
        for evt, elem in events:
            if evt == 'end' and elem.tag == 'event':
                time = int(float(elem.get('time')))
                population.parse_event(elem)

            count += 1
            if time >= n:
                log.info(f'Simulation analysis at {hhmmss(time)} with {count} '
                    'events processed.')
                n += 3600
            if count % 100000 == 0:
                root.clear()
        
        log.info('Closing events file and completing parsing.')
        root.clear()
        eventsfile.close()

        log.info('Processing and analyzing results.')
        population.filter_agents(lambda agent: str(agent.id).isdigit())
        population.cleanup(time)

        log.info('Dumping results to database.')
        agents = population.export_agents()
        activities = population.export_activities()
        legs = population.export_legs()
        self.create_tables()
        self.database.insert_values('output_agents', agents, 3)
        self.database.insert_values('output_activities', activities, 7)
        self.database.insert_values('output_legs', legs, 7)
        self.create_indexes()
        self.database.connection.commit()