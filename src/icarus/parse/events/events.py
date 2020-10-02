
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


    def create_tables(self):
        tables = ('temp_agents', 'temp_activities', 'temp_legs', 
            'temp_events', 'events', 'temp_temporary')
        self.database.drop_table(*tables)
        query = '''
            CREATE TABLE temp_agents (
                agent_id MEDIUMINT UNSIGNED,
                abort TINYINT UNSIGNED
            );
        '''
        self.database.cursor.execute(query)
        query = '''
            CREATE TABLE temp_activities (
                agent_id MEDIUMINT UNSIGNED,
                agent_idx TINYINT UNSIGNED,
                sim_start MEDUMINT UNSIGNED,
                sim_end MEDIUMINT UNSIGNED,
                abort TINYINT UNSIGNED
            );
        '''
        self.database.cursor.execute(query)
        query = '''
            CREATE TABLE temp_legs (
                agent_id MEDIUMINT UNSIGNED,
                agent_idx TINYINT UNSIGNED,
                sim_start MEDUMINT UNSIGNED,
                sim_end MEDIUMINT UNSIGNED,
                abort TINYINT UNSIGNED
            )
        '''
        self.database.cursor.execute(query)
        query = '''
            CREATE TABLE temp_events (
                event_id INT UNSIGNED,
                agent_id MEDIUMINT UNSIGNED,
                agent_idx SMALLINT UNSIGNED,
                leg_idx SMALLINT UNSIGNED,
                link_id VARCHAR(255),
                sim_start MEDIUMINT UNSIGNED,
                sim_end MEDIUMINT UNSINGED
            );
        '''
        self.database.cursor.execute(query)
        self.database.connection.commit()


    def merge_agents(self):
        log.debug('Creating temprorary index for agents join.')
        query = '''
            CREATE INDEX temp_agents_agent
            ON temp_agents(agent_id);
        '''
        self.database.cursor.execute(query)

        log.debug('Merging agents tables.')
        query = '''
            CREATE TABLE temp_temporary
            AS SELECT
                agents.agent_id AS agent_id,
                agents.household_id AS household_id,
                agents.household_idx AS household_idx,
                agents.uses_vehicle AS uses_vehicle,
                agents.uses_walk AS uses_walk,
                agents.uses_bike AS uses_bike,
                agents.uses_transit AS uses_transit,
                agents.uses_party AS uses_party,
                temp_agents.abort AS abort,
                NULL AS exposure
            FROM agents
            LEFT JOIN temp_agents
            USING(agent_id);
        '''
        self.database.cursor.execute(query)

        log.debug('Checking table integrity.')
        rows0 = self.database.count_rows('agents')
        rows1 = self.database.count_rows('temp_temporary')
        if rows0 != rows1:
            log.error('Table misalignment while merging agents; '
                'aborting process to prevent data loss.')
            raise RuntimeError

        log.debug('Dropping old table and renaming.')
        self.database.drop_table('temp_agents', 'agents')
        query = '''
            ALTER TABLE temp_temporary
            RENAME TO agents;
        '''
        self.database.cursor.execute(query)
        self.database.connection.commit()


    def merge_activities(self):
        log.debug('Creating temprorary index for activities join.')
        query = '''
            CREATE INDEX temp_activities_agent
            ON temp_activities(agent_id, agent_idx);
        '''
        self.database.cursor.execute(query)

        log.debug('Merging activities tables.')
        query = '''
            CREATE TABLE temp_temporary
            AS SELECT
                activities.activity_id AS activity_id,
                activities.agent_id AS agent_id,
                activities.agent_idx AS agent_idx,
                activities.type AS type,
                activities.apn AS apn,
                activities."group" AS "group",
                activities.abm_start AS abm_start,
                activities.abm_end AS abm_end,
                temp_activities.sim_start AS sim_start,
                temp_activities.sim_end AS sim_end,
                temp_activities.abort AS abort,
                NULL AS exposure
            FROM activities
            LEFT JOIN temp_activities
            USING(agent_id, agent_idx);
        '''
        self.database.cursor.execute(query)

        log.debug('Checking table integrity.')
        rows0 = self.database.count_rows('activities')
        rows1 = self.database.count_rows('temp_temporary')
        if rows0 != rows1:
            log.error('Table misalignment while merging activities; '
                'aborting process to prevent data loss.')
            raise RuntimeError

        log.debug('Dropping old table and renaming.')
        self.database.drop_table('temp_activities', 'activities')
        query = '''
            ALTER TABLE temp_temporary
            RENAME TO activities;
        '''
        self.database.cursor.execute(query)
        self.database.connection.commit()


    def merge_legs(self):
        log.debug('Creating temprorary index for legs join.')
        query = '''
            CREATE INDEX temp_legs_agent
            ON temp_legs(agent_id, agent_idx);
        '''
        self.database.cursor.execute(query)

        log.debug('Merging legs tables.')
        query = '''
            CREATE TABLE temp_temporary
            AS SELECT
                legs.leg_id AS leg_id,
                legs.agent_id AS agent_id,
                legs.agent_idx AS agent_idx,
                legs.mode AS mode,
                legs.party AS party,
                legs.abm_start AS abm_start,
                legs.abm_end AS abm_end,
                temp_legs.sim_start AS sim_start,
                temp_legs.sim_end AS sim_end,
                temp_legs.abort AS abort,
                NULL AS exposure
            FROM legs
            LEFT JOIN temp_legs
            USING(agent_id, agent_idx);
        '''
        self.database.cursor.execute(query)

        log.debug('Checking table integrity.')
        rows0 = self.database.count_rows('legs')
        rows1 = self.database.count_rows('temp_temporary')
        if rows0 != rows1:
            log.error('Table misalignment while merging legs; '
                'aborting process to prevent data loss.')
            raise RuntimeError

        log.debug('Dropping old table and renaming.')
        self.database.drop_table('temp_legs', 'legs')
        query = '''
            ALTER TABLE temp_temporary
            RENAME TO legs;
        '''
        self.database.cursor.execute(query)
        self.database.connection.commit()


    def merge_events(self):
        log.debug('Creating temprorary index for legs join.')
        query = '''
            CREATE INDEX temp_events_agent
            ON temp_events(agent_id, agent_idx, leg_idx);
        '''
        self.database.cursor.execute(query)

        log.debug('Merging legs tables.')
        query = '''
            CREATE TABLE events
            AS SELECT
                temp_events.event_id AS event_id,
                legs.leg_id AS leg_id,
                temp_events.leg_idx AS leg_idx,
                temp_events.link_id AS link_id,
                temp_events.sim_start AS sim_start,
                temp_events.sim_end AS sim_end,
                CAST(NULL AS INT) AS air_exposure,
                CAST(NULL AS INT) AS mrt_exposure
            FROM temp_events
            INNER JOIN legs
            ON temp_events.agent_id = legs.agent_id
            AND temp_events.agent_idx = legs.agent_idx;
        '''
        self.database.cursor.execute(query)

        log.debug('Dropping old tables.')
        self.database.drop_table('temp_events')
        self.database.connection.commit()

    
    def create_indexes(self):
        query = 'CREATE INDEX agents_agent ON agents(agent_id);'
        self.database.connection.execute(query)
        query = 'CREATE INDEX agents_household ON agents(household_id, household_idx);'
        self.database.connection.execute(query)
        query = 'CREATE INDEX legs_leg ON legs(leg_id);'
        self.database.connection.execute(query)
        query = 'CREATE INDEX legs_agent ON legs(agent_id, agent_idx);'
        self.database.connection.execute(query)
        query = 'CREATE INDEX activities_activity ON activities(activity_id);'
        self.database.connection.execute(query)
        query = 'CREATE INDEX activities_agent ON activities(agent_id, agent_idx);'
        self.database.connection.execute(query)
        query = 'CREATE INDEX activities_parcel ON activities(apn);'
        self.database.connection.execute(query)
        query = 'CREATE INDEX events_event ON events(event_id);'
        self.database.cursor.execute(query)
        query = 'CREATE INDEX events_link ON events(link_id);'
        self.database.cursor.execute(query)
        query = 'CREATE INDEX events_leg ON events(leg_id, leg_idx);'
        self.database.cursor.execute(query)
        self.database.connection.commit()
    

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
        return False

    
    def parse(self, planspath, eventspath):
        log.info('Reallocating tables for simulation output data.')
        self.create_tables()

        log.info('Loading and building network.')
        network = Network(self.database)
        network.load_network(planspath)
        population = Population(network)

        log.info('Decompressing and loading events file.')
        eventsfile = multiopen(eventspath, mode='rb')
        events = iter(iterparse(eventsfile, events=('start', 'end')))
        evt, root = next(events)

        count = 0
        time = 14400
        n = 14400

        log.info('Iterating over simulation events and parsing data.')
        log.debug('Starting events parsing.')
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

                log.debug('Exporting completed events.')
                events = population.export_events()
                self.database.insert_values('temp_events', events, 7)

                log.debug('Exporting completed activities.')
                activities = population.export_activities()
                self.database.insert_values('temp_activities', activities, 5)

                log.debug('Exporting completed legs.')
                legs = population.export_legs()
                self.database.insert_values('temp_legs', legs, 5)

                self.database.connection.commit()

                log.debug('Continuing events parsing.')
                del activities, legs, events
                
        log.info('Simulation events iteration complete; cleaning up.')
        root.clear()

        log.debug('Closing final activities.')
        population.cleanup(time)

        log.debug('Exporting remaining events.')
        events = population.export_events()
        self.database.insert_values('temp_events', events, 7)

        log.debug('Exporting remaining activities.')
        activities = population.export_activities()
        self.database.insert_values('temp_activities', activities, 5)

        log.debug('Exporting remaining legs.')
        legs = population.export_legs()
        self.database.insert_values('temp_legs', legs, 5)

        log.debug('Exporting all agents.')
        agents = population.export_agents()
        self.database.insert_values('temp_agents', agents, 2)

        del events, activities, legs, agents, population, network
        self.database.connection.commit()

        log.info('Merging and updating tables.')

        log.debug('Merging and updating agents.')
        self.merge_agents()

        log.debug('Merging and updating activities.')
        self.merge_activities()

        log.debug('Merging and updating legs.')
        self.merge_legs()

        log.debug('Merging and updating events.')
        self.merge_events()

        log.info('Creating indexes on new tables.')
        self.create_indexes()
