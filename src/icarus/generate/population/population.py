
import logging as log
from typing import Callable

from icarus.generate.population.network import Network
from icarus.generate.population.subpopulation import Subpopulation
from icarus.generate.population.trip import Trip
from icarus.generate.population.party import Party
from icarus.generate.population.agent import Agent, Leg
from icarus.generate.population.types import Mode, ActivityType, RouteMode
from icarus.util.sqlite import SqliteUtil
from icarus.util.general import chunk, defaultdict


class Population:
    def __init__(self, database: SqliteUtil):
        self.database = database

    
    def create_tables(self):
        self.database.drop_table('agents', 'activities', 'legs')
        self.database.cursor.execute('''
            CREATE TABLE agents(
                agent_id MEDIUMINT UNSIGNED,
                household_id MEDIUMINT UNSIGNED,
                household_idx SMALLINT UNSIGNED,
                plan_size TINYINT UNSIGNED,
                uses_vehicle TINYINT UNSIGNED,
                uses_walk TINYINT UNSIGNED,
                uses_bike TINYINT UNSIGNED,
                uses_transit TINYINT UNSIGNED,
                uses_party TINYINT UNSIGNED
            );  ''')
        self.database.cursor.execute('''
            CREATE TABLE activities(
                activity_id INT UNSIGNED,
                agent_id MEDIUMINT UNSIGNED,
                agent_idx TINYINT UNSIGNED,
                type VARCHAR(255),
                apn VARCHAR(255),
                `group` MEDIUMINT UNSIGNED,
                start MEDUMINT UNSIGNED,
                end MEDIUMINT UNSIGNED,
                duration MEDIUMINT UNSIGNED
            );  ''')
        self.database.cursor.execute('''
            CREATE TABLE legs(
                leg_id INT UNSIGNED,
                agent_id MEDIUMINT UNSIGNED,
                agent_idx TINYINT UNSIGNED,
                mode VARCHAR(255),
                party MEDIUMINT UNSIGNED,
                start MEDIUMINT UNSIGNED,
                end MEDIUMINT UNSIGNED,
                duration MEDIUMINT UNSIGNED
            );  ''')
        self.database.connection.commit()


    def fetch_trips(self, min_household, max_household):
        self.database.cursor.execute(f'''
            SELECT
                hhid,
                pnum,
                personTripNum,
                jointTripRole,
                party,
                origTaz,
                origMaz,
                destTaz,
                destMaz,
                origPurp,
                destPurp,
                mode,
                vehId,
                isamAdjDepMin,
                isamAdjArrMin,
                isamAdjDurMin
            FROM trips
            WHERE hhid >= {min_household}
            AND hhid < {max_household}; ''')
        return self.database.cursor.fetchall()


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


    def fetch_max(self, table, column):
        self.database.cursor.execute(f'SELECT MAX({column}) FROM {table};')
        return self.database.cursor.fetchall()[0][0]

    
    def ready(self):
        tables = ('trips', 'regions', 'parcels')
        exists = self.database.table_exists(*tables)
        if len(exists) < len(tables):
            missing = ', '.join(set(tables) - set(exists))
            log.info(f'Could not find tables {missing} in database.')
        return len(exists) == len(tables)


    def complete(self):
        tables = ('agents', 'activities', 'legs')
        exists = self.database.table_exists(*tables)
        if len(exists):
            present = ', '.join(exists)
            log.info(f'Found tables {present} already in database.')
        return len(exists) > 0
    

    def generate(self, modes=None, activity_types=None, seed=None):
        log.info('Loading process metadata.')
        size = self.fetch_max('households', 'hhid')

        if modes is None:
            modes = set(Mode)
        else:
            modes = set((Mode(mode) for mode in modes))
        if activity_types is None:
            activity_types = set(ActivityType)
        else:
            activity_types = set((ActivityType(act) for act in activity_types))

        log.info('Preparing tables for population.')
        self.create_tables()
        
        log.info('Loading network data.')
        network = Network(self.database)
        network.load_network()

        log.info('Iterating over trips for each household.')

        error = defaultdict(int)

        def valid_party(party: Party) -> bool:
            return party.driver is not None or party.mode != RouteMode.CAR

        def valid_leg(leg: Leg) -> bool:
            distance = network.minimum_distance(leg.party.origin_group.maz, 
                leg.party.dest_group.maz)
            duration = leg.end - leg.start
            valid = False
            if duration > 0:
                valid = distance / duration < leg.mode.route_mode().max_speed()
            elif distance == 0:
                valid = True
            return valid

        def valid_agent(agent: Agent) -> bool:
            return (agent.modes.issubset(modes)
                and agent.activity_types.issubset(activity_types)
                and agent.mazs.issubset(network.mazs)
                and all(valid_party(party) for party in agent.parties)
                and all(valid_leg(leg) for leg in agent.legs))

        # def valid_agent(agent: Agent) -> bool:
        #     valid = True
        #     if not agent.modes.issubset(modes):
        #         error['mode'] += 1
        #         valid = False
        #     if not agent.activity_types.issubset(activity_types):
        #         error['activity'] += 1
        #         valid = False
        #     if any(not valid_party(party) for party in agent.parties):
        #             error['party'] += 1
        #             valid = False
        #     if not agent.mazs.issubset(network.mazs):
        #         error['maz'] += 1
        #         valid = False
        #     elif any(not valid_leg(leg) for leg in agent.legs):
        #         error['leg'] += 1
        #         valid = False
        #     return valid

        for min_household, max_household in chunk(0, size, 100000):
            log.info(f'Fetching trips from household {min_household}'
                f' to {max_household}.')
            subpopulation = Subpopulation()
            trips = self.fetch_trips(min_household, max_household)

            log.info('Parsing fetched trips.')
            for trip_data in trips:
                trip = Trip(trip_data)
                subpopulation.parse_trip(trip)

            log.info('Filtering agents.')
            subpopulation.filter(valid_agent)
            log.info('Cleaning up population.')
            subpopulation.clean()
            log.info('Assigning parcels to activities.')
            subpopulation.assign_parcels(network)
            log.info('Identifying activity, leg and agent ids.')
            subpopulation.identify()

            log.info('Writing generated population to database.')
            agents = subpopulation.export_agents()
            self.database.insert_values('agents', agents, 9)
            activities = subpopulation.export_activities()
            self.database.insert_values('activities', activities, 9)
            legs = subpopulation.export_legs()
            self.database.insert_values('legs', legs, 8)
            self.database.connection.commit()

        self.create_indexes()
        self.database.connection.commit()
