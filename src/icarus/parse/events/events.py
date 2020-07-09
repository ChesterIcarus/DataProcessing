
import logging as log
from xml.etree.ElementTree import iterparse

from icarus.parse.events.network import Network
from icarus.parse.events.activity import Activity
from icarus.parse.events.leg import Leg
from icarus.parse.events.population import Population
from icarus.util.sqlite import SqliteUtil
from icarus.util.general import defaultdict, counter
from icarus.util.file import multiopen, exists


def hhmmss(secs):
    hh = secs // 3600
    secs -= hh * 3600
    mm = secs // 60
    secs -= mm * 60
    ss = secs
    return f'{str(hh).zfill(2)}:{str(mm).zfill(2)}:{str(ss).zfill(2)}'


class Events:
    def __init__(self, database):
        self.database = database
        self.legs = defaultdict(lambda x: [])
        self.activities = defaultdict(lambda x: [])


    def create_tables(self):
        self.database.drop_table('output_agents', 'output_activities', 
            'output_legs', 'output_events')
        self.database.cursor.execute('''
            CREATE TABLE output_agents (
                agent_id MEDIUMINT UNSIGNED,
                plan_size TINYINT UNSIGNED,
                exposure FLOAT
            );  ''')
        self.database.cursor.execute('''
            CREATE TABLE output_activities (
                activity_id INT UNSIGNED,
                agent_id MEDIUMINT UNSIGNED,
                agent_idx TINYINT UNSINGED,
                type VARCHAR(255),
                link_id VARCHAR(255),
                start MEDIUMINT UNISGNED,
                end MEDIUMINT UNSIGNED,
                duration MEDIUMINT UNSIGNED,
                exposure FLOAT
            );  ''')
        self.database.cursor.execute('''
            CREATE TABLE output_legs (
                leg_id INT UNSIGNED,
                agent_id MEDIUMINT UNSIGNED,
                agent_idx MEDIUMINT UNSIGNED,
                mode VARCHAR(255),
                start MEDIUMINT UNISGNED,
                end MEDIUMINT UNSIGNED,
                duration MEDIUMINT UNSIGNED,
                exposure FLOAT
            );  ''')
        self.database.cursor.execute('''
            CREATE TABLE output_events (
                event_id INT UNSIGNED,
                leg_id INT UNSIGNED,
                leg_idx SMALLINT UNSINGED,
                link_id VARCHAR(255),
                start MEDIUMINT UNSIGNED,
                end MEDIUMINT UNSINGED,
                duration MEDIUMINT UNSIGNED,
                exposure FLOAT
            );  ''')
        self.database.connection.commit()

    
    def create_indexes(self):
        query = '''
            CREATE INDEX output_agents_agent 
            ON output_agents(agent_id);'''
        self.database.cursor.execute(query)
        query = '''
            CREATE INDEX output_activities_agent
            ON output_activities(agent_id, agent_idx);'''
        self.database.cursor.execute(query)
        query = '''
            CREATE INDEX output_activities_activity
            ON output_activities(activity_id);'''
        self.database.cursor.execute(query)
        query = '''
            CREATE INDEX output_legs_agent 
            ON output_legs(agent_id, agent_idx);'''
        self.database.cursor.execute(query)
        query = '''
            CREATE INDEX output_legs_leg
            ON output_legs(leg_id);'''
        self.database.cursor.execute(query)
        query = '''
            CREATE INDEX output_events_event
            ON output_events(event_id)
        '''
        self.database.cursor.execute(query)
        query = '''
            CREATE INDEX output_events_link
            ON output_events(link_id)
        '''
        self.database.cursor.execute(query)
        query = '''
            CREATE INDEX output_events_leg
            ON output_events(leg_id, leg_idx)
        '''
        self.database.cursor.execute(query)
        self.database.connection.commit()

    
    def fetch_legs(self):
        query = '''
            SELECT
                leg_id,
                agent_id
            FROM legs
            ORDER BY 
                agent_id,
                agent_idx;  '''
        self.database.cursor.execute(query)
        return self.database.cursor.fetchall()


    def load_legs(self):
        log.info('Loading input leg definitions.')
        legs = counter(self.fetch_legs(), 'Loading leg %s.')
        for leg_id, agent_id in legs:
            self.legs[str(agent_id)].append(leg_id)

    
    def fetch_activities(self):
        query = '''
            SELECT
                activity_id,
                agent_id
            FROM activities
            ORDER BY 
                agent_id,
                agent_idx;  '''
        self.database.cursor.execute(query)
        return self.database.cursor.fetchall()


    def load_activities(self):
        log.info('Loading input activity definitions.')
        activities = counter(self.fetch_activities(), 'Loading activity %s.')
        for activitiy_id, agent_id in activities:
            self.activities[str(agent_id)].append(activitiy_id)


    def ready(self, eventspath, planspath):
        ready = True
        if not exists(planspath):
            log.warn(f'Could not find file {planspath} in run files.')
            ready = False
        if not exists(eventspath):
            log.warn(f'Could not find file {eventspath} in run files.')
            ready = False
        return ready

    
    def complete(self):
        tables = ('output_agents', 'output_activities', 
            'output_legs', 'output_events')
        exists = self.database.table_exists(*tables)
        if len(exists):
            present = ', '.join(exists)
            log.warn(f'Found tables {present} already in database.')
        return len(exists) > 0

    
    def parse(self, planspath, eventspath):
        log.info('Reallocating tables for simulation output data.')
        self.create_tables()

        log.info('Loading and building network.')
        network = Network(self.database)
        network.load_network(planspath)
        population = Population(network)

        log.info('Loading input data identifications.')
        self.load_activities()
        self.load_legs()
        Activity.activities = self.activities
        Leg.legs = self.legs

        log.info('Decompressing and loading events file.')
        eventsfile = multiopen(eventspath, mode='rb')
        events = iter(iterparse(eventsfile, events=('start', 'end')))
        evt, root = next(events)

        count = 0
        time = 14400
        n = 14400

        log.info('Iterating over simulation events and parsing data.')
        for evt, elem in events:
            if evt == 'end' and elem.tag == 'event':
                time = int(float(elem.get('time')))
                population.parse_event(elem)

            count += 1
            if time >= n:
                log.info(f'Simulation events parsing at {hhmmss(time)} '
                    f'with {count} events processed.')
                n += 3600
            if count % 1000000 == 0:
                root.clear()
                
                log.debug('Exporting finished activities, legs and events.')
                activities = population.export_activities()
                events = population.export_events()
                legs = population.export_legs()
                
                log.debug('Pushing parsed event data to database.')
                self.database.insert_values('output_activities', activities, 9)
                self.database.insert_values('output_events', events, 8)
                self.database.insert_values('output_legs', legs, 8)
                self.database.connection.commit()

        root.clear()

        log.info('Simulation events iteration complete; cleaning up.')

        log.debug('Closing final activities.')
        population.cleanup(time)

        log.debug('Exporting finished activities, legs and events.')
        activities = population.export_activities()
        events = population.export_events()
        legs = population.export_legs()
        agents = population.export_agents()

        log.debug('Pushing parsed event data to database.')
        self.database.insert_values('output_agents', agents, 3)
        self.database.insert_values('output_activities', activities, 9)
        self.database.insert_values('output_events', events, 8)
        self.database.insert_values('output_legs', legs, 8)

        log.info('Creating indexes on new tables.')
        self.create_indexes()
