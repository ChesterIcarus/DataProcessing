
import logging as log

from icarus.analyze.exposure.network import Network
from icarus.analyze.exposure.population import Population
from icarus.util.general import bins
from icarus.util.apsw import Database


class Exposure:
    def __init__(self, database: Database):
        self.database = database
        self.network = Network(database)
        self.population = Population(database, self.network)
    

    def fetch_agents(self):
        query = 'SELECT agent_id FROM agents WHERE abort = 0;'
        self.database.cursor.execute(query)
        return self.database.cursor.fetchall()

    
    def create_tables(self):
        self.database.drop_table('temp_agents', 'temp_activities', 
            'temp_legs', 'temp_events')
        query = f'''
            CREATE TABLE temp_agents
            AS SELECT * FROM agents
            WHERE FALSE;
        '''
        self.database.cursor.execute(query)
        query = f'''
            CREATE TABLE temp_legs
            AS SELECT * FROM legs
            WHERE FALSE;
        '''
        self.database.cursor.execute(query)
        query = f'''
            CREATE TABLE temp_activities
            AS SELECT * FROM activities
            WHERE FALSE;
        '''
        self.database.cursor.execute(query)
        query = f'''
            CREATE TABLE temp_events
            AS SELECT * FROM events
            WHERE FALSE;
        '''
        self.database.cursor.execute(query)
        self.database.connection.commit()

    
    def create_indexes(self):
        query = '''
            CREATE INDEX output_agents_agent 
            ON output_agents(agent_id);
        '''
        self.database.cursor.execute(query)
        query = '''
            CREATE INDEX output_activities_agent
            ON output_activities(agent_id, agent_idx);
        '''
        self.database.cursor.execute(query)
        query = '''
            CREATE INDEX output_activities_activity
            ON output_activities(activity_id);
        '''
        self.database.cursor.execute(query)
        query = '''
            CREATE INDEX output_legs_agent 
            ON output_legs(agent_id, agent_idx);
        '''
        self.database.cursor.execute(query)
        query = '''
            CREATE INDEX output_legs_leg
            ON output_legs(leg_id);'''
        self.database.cursor.execute(query)
        query = '''
            CREATE INDEX output_events_event
            ON output_events(event_id);
        '''
        self.database.cursor.execute(query)
        query = '''
            CREATE INDEX output_events_link
            ON output_events(link_id);
        '''
        self.database.cursor.execute(query)
        query = '''
            CREATE INDEX output_events_leg
            ON output_events(leg_id, leg_idx);
        '''
        self.database.cursor.execute(query)
        self.database.connection.commit()


    def verify_tables(self):
        original_count = (
            self.database.count_rows('output_agents'),
            self.database.count_rows('output_activities'),
            self.database.count_rows('output_legs'),
            self.database.count_rows('output_events')
        )
        result_count = (
            self.database.count_rows('temp_agents'),
            self.database.count_rows('temp_activities'),
            self.database.count_rows('temp_legs'),
            self.database.count_rows('temp_events')
        )
        return original_count == result_count


    def rename_tables(self):
        self.database.drop_table('output_agents', 'output_activities', 
            'output_legs', 'output_events')
        query = f'''
            ALTER TABLE temp_agents
            RENAME TO output_agents;
        '''
        self.database.cursor.execute(query)
        query = f'''
            ALTER TABLE temp_legs
            RENAME TO output_legs;
        '''
        self.database.cursor.execute(query)
        query = f'''
            ALTER TABLE temp_activities
            RENAME TO output_activities;
        '''
        self.database.cursor.execute(query)
        query = f'''
            ALTER TABLE temp_events
            RENAME TO output_events;
        '''
        self.database.cursor.execute(query)
        self.database.connection.commit()

    
    def ready(self):
        # tables = ('output_activities', 'output_legs', 'output_agents', 'output_events')
        # present = self.database.table_exists(*tables)
        # if len(present) < len(tables):
        #     missing = ', '.join(set(tables) - set(present))
        #     log.info(f'Could not find tables {missing} in database.')
        # return len(present) == len(tables)
        return True

    
    def complete(self):
        return False
        
    
    def analyze(self, source: str):
        log.info('Allocating tables for exposure analysis.')
        self.database.drop_temporaries()
        self.create_tables()

        log.info('Loading network data.')
        self.network.load_network(source)

        log.info('Identifying agents to analyze.')
        uuids = tuple(uuid[0] for uuid in self.fetch_agents())

        query_agents = '''
            UPDATE agents
            SET exposure = ?
            WHERE agent_id = ?;
        '''

        query_acts = '''
            UPDATE activities
            SET exposure = ?
            WHERE activity_id = ?;
        '''

        query_legs = '''
            UPDATE legs
            SET exposure = ?
            WHERE leg_id = ?;
        '''

        query_evts = '''
            UPDATE events
            SET exposure = ?
            WHERE event_id = ?;
        '''

        log.info('Iterating over agent data and analyzing exposure.')
        count = 0
        for uuid_bin in bins(uuids, 100000):
            log.debug('Creating sample population.')
            self.population.create_population(uuid_bin)

            log.debug('Loading population legs, activities and events.')
            self.population.load_population()

            log.debug('Calculating exposure on all agent data.')
            self.population.calculate_exposure()

            log.debug('Exporting population to database.')
            agents = self.population.export_agents()
            activities = self.population.export_activities()
            legs = self.population.export_legs()
            events = self.population.export_events()

            self.database.cursor.executemany(query_agents, agents)
            self.database.cursor.executemany(query_acts, activities)
            self.database.cursor.executemany(query_legs, legs)
            self.database.cursor.executemany(query_evts, events)
            self.population.delete_population()
            self.database.connection.commit()

            del agents, activities, legs, events

            count += len(uuid_bin)
            log.info(f'Exposure analysis at agent {count}.')

        log.info('Updating network properties.')

        query = '''
            UPDATE links
            SET exposure = ?
            WHERE link_id = ?;
        '''
        dump = ((link.exposure, link.id) 
            for link in self.network.links.values())
        self.database.cursor.executemany(query, dump)
        self.database.connection.commit()

        # log.info('Verify integrity of results.')
        # if not self.verify_tables():
        #     log.error('Input and output table sizes did not match.')
        #     log.error('Terminating without saving to prevent data loss.')
        #     raise RuntimeError

        # log.info('Renaming data and dropping old tables.')
        # self.rename_tables()

        # log.info('Creating indexes on new tables.')
        # self.create_indexes()
