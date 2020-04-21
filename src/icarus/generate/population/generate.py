
import logging as log
from icarus.input.objects.network import Network
from icarus.input.objects.population import Population
from icarus.input.objects.trip import Trip
from icarus.input.objects.mode import Mode
from icarus.input.objects.activity_type import ActivityType
from icarus.util.general import chunk

class Generation:
    def __init__(self, database):
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
                stop MEDIUMINT UNSIGNED,
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

    
    def fetch_parcels(self):
        self.database.cursor.execute(f'''
            SELECT
                apn,
                maz,
                type
            FROM parcels
            ORDER BY 
                RANDOM(); ''')

        return self.database.cursor.fetchall()


    def fetch_count(self, table):
        self.database.cursor.execute(f'SELECT COUNT(*) FROM {table};')
        return self.database.cursor.fetchall()[0][0]


    def complete(self):
        tables = ('agents', 'activities', 'legs')
        return len(self.database.table_exists(*tables)) == len(tables)
    

    def generate(self, modes=None, activity_types=None, seed=None):
        log.info('Dropping and creating tables for plans.')
        self.create_tables()
        
        log.info('Fetching network data.')
        parcels = self.fetch_parcels()
        size = self.fetch_count('households')
        network = Network(parcels)
        del parcels

        if modes is None:
            modes = set(Mode)
        else:
            modes = set((Mode(mode) for mode in modes))
        if activity_types is None:
            activity_types = set(ActivityType)
        else:
            activity_types = set((ActivityType(act) for act in activity_types))

        valid = (lambda agent:
            agent.modes.issubset(modes) and 
            agent.activity_types.issubset(activity_types) and
            agent.mazs.issubset(network.mazs) and 
            all((party.driver is not None for party in agent.parties )))

        log.info('Iterating over trips for each household.')
        for min_household, max_household in chunk(0, size, 100000):
            log.info(f'Fetching trips from household {min_household}'
                f' to {max_household}.')
            subpopulation = Population()
            trips = self.fetch_trips(min_household, max_household)

            log.info('Parsing fetched trips.')
            for trip_data in trips:
                trip = Trip(trip_data)
                subpopulation.parse_trip(trip)

            log.info('Filtering agents.')
            subpopulation.filter(valid)
            log.info('Cleaning up subpopulation.')
            subpopulation.clean()
            log.info('Assigning parcels to activities.')
            subpopulation.assign_parcels(network)
            log.info('Identifying activities, legs, etc.')
            subpopulation.identify()

            log.info('Writing generated population to database.')
            agents = subpopulation.export_agents()
            self.database.insert_values('agents', agents, 9)
            activities = subpopulation.export_activities()
            self.database.insert_values('activities', activities, 9)
            legs = subpopulation.export_legs()
            self.database.insert_values('legs', legs, 8)
            self.database.connection.commit()