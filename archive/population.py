
import csv
import logging as log

from random import randint
from enum import IntEnum

from icarus.input.objects import *
from icarus.util.file import multiopen
from icarus.util.general import chunk, defaultdict


class Population:
    def __init__(self, database):
        self.database = database


    def load_trips(self, trips_file):
        open_file = open(trips_file, 'r')
        trips = csv.reader(open_file, delimiter=',', quotechar='"')
        _ = next(trips)

        count = 0
        n = 1

        for trip in trips:
            yield [int(t) for t in trip[0:6]] + [trip[6]] + \
                [int(t) for t in trip[7:15]] + [float(t) for t in trip[15:18]]
            count += 1
            if count == n:
                log.info(f'Parsed trip {count}.')
                n <<= 1
        if count != n << 1:
            log.info(f'Parsed trip {count}.')
        open_file.close()


    def load_households(self, households_file):
        open_file = open(households_file, 'r')
        households = csv.reader(open_file, delimiter=',', quotechar='"')
        _ = next(households)

        count = 0
        n = 1

        for household in households:
            yield [int(h) for h in household[0:2]] + [float(household[2])] + \
                [int(h) for h in household[3:17]]
            count += 1
            if count == n:
                log.info(f'Parsed household {count}.')
                n <<= 1
        if count != n << 1:
            log.info(f'Parsed household {count}.')
        open_file.close()


    def load_persons(self, persons_file):
        open_file = open(persons_file, 'r')
        persons = csv.reader(open_file, delimiter=',', quotechar='"')
        _ = next(persons)

        count = 0
        n = 1

        for person in persons:
            yield [int(p) for p in person[0:2]] + [float(person[2])] + \
                [int(p) for p in person[3:18]] + [person[18]] + \
                [int(p) for p in person[19:37]] + [person[37]] + [int(person[38])]
            count += 1
            if count == n:
                log.info(f'Parsed person {count}.')
                n <<= 1
        if count != n << 1:
            log.info(f'Parsed person {count}.')
        open_file.close()


    def parse_trips(self, trips_file):
        trips = self.load_trips(trips_file)
        self.database.drop_table('trips')
        self.database.cursor.execute('''
            CREATE TABLE trips(
                hhid_uniqueid INT UNSIGNED,
                uniqueid SMALLINT UNSIGNED,
                hhid MEDIUMINT UNSIGNED,
                pnum TINYINT UNSIGNED,
                personTripNum TINYINT UNISGNED,
                jointTripRole TINYINT UNSIGNED,
                party VARCHAR(255),
                origTaz SMALLINT UNSIGNED,
                origMaz SMALLINT UNSIGNED,
                destTaz SMALLINT UNSIGNED,
                destMaz SMALLINT UNSIGNED,
                origPurp SMALLINT UNSIGNED,
                destPurp SMALLINT UNSIGNED,
                mode TINYINT UNSIGNED,
                vehId TINYINT,
                isamAdjDepMin FLOAT,
                isamAdjArrMin FLOAT,
                isamAdjDurMin FLOAT
            );  ''')
        self.database.cursor.executemany(
            f'INSERT INTO trips VALUES({", ".join("?"*18)});', trips)
        self.database.cursor.execute(
            'CREATE UNIQUE INDEX trips_trip ON trips'
            '(hhid, pnum, personTripNum)')
        self.database.connection.commit()


    def parse_households(self, households_file):
        households = self.load_households(households_file)
        self.database.drop_table('households')
        self.database.cursor.execute('''
            CREATE TABLE households(
                hhid MEDIUMINT UNSIGNED,
                hhidAcrossSample MEDIUMINT UNSIGNED,
                pumsSerialNo FLOAT,
                homeTaz SMALLLINT UNSIGNED,
                homeMaz SMALLINT UNSIGNED,
                hhsize TINYINT UNSINGED,
                numFtWorkers TINYINT UNSIGNED,
                numPtWorkers TINYINT UNSIGNED,
                numUnivStuds TINYINT UNSIGNED,
                numNonWorkers TINYINT UNSIGNED
                numRetired TINYINT UNSIGNED,
                numDrivAgeStuds TINYINT UNSIGNED,
                numPreDrivStuds TINYINT UNSIGNED,
                numPreschool TINYINT UNSIGNED,
                hhIncomeDollar MEDIUMINT UNSIGNED,
                hhNumAutos TINYINT UNSIGNED,
                dwellingType TINYINT UNSIGNED,
                ifAvHousehold TINYINT UNSIGED
            );  ''')
        self.database.cursor.executemany(
            f'INSERT INTO households VALUES({", ".join("?"*17)});', households)
        self.database.cursor.execute(
            'CREATE UNIQUE INDEX household_households ON households(hhid)')
        self.database.connection.commit()


    def parse_persons(self, persons_file):
        persons = self.load_persons(persons_file)
        self.database.drop_table('persons')
        self.database.cursor.execute('''
            CREATE TABLE persons(
                hhid MEDIUMINT UNSIGNED,
                pnum MEDIUMINT UNSIGNED,
                pumsSerialNo FLOAT,
                persType TINYINT UNSIGNED,
                personTypeDetailed TINYINT UNSIGNED,
                age TINYINT UNSIGNED,
                gender TINYINT UNSIGNED,
                industry TINYINT UNSIGNED,
                schlGrade TINYINT UNSIGNED,
                educLevel TINYINT UNSIGNED,
                workPlaceType TINYINT UNSIGNED,
                workPlaceTaz SMALLINT UNISNGED,
                workPlaceMaz SMALLINT UNISNGED,
                schoolType TINYINT UNSIGNED,
                schoolTaz SMALLINT UNSIGNED,
                schoolMaz SMALLINT UNISGNED,
                campusBusinessTaz SMALLINT UNSIGNED,
                campusBusinessMaz SMALLINT UNSIGNED,
                usualCarID TINYINT UNSIGNED,
                dailyActivityPattern TINYINT UNSIGNED,
                specEvtParticipant TINYINT UNSIGNED,
                jointTour1Role TINYINT UNSIGNED,
                jointTour2Role TINYINT UNSIGNED,
                obPeChauffBund1 TINYINT UNSIGNED,
                obPeChauffBund2 TINYINT UNSIGNED,
                obPeChauffBund3 TINYINT UNSIGNED,
                obRsChauffBund TINYINT UNSIGNED,
                obPePassBund TINYINT UNSIGNED,
                obRsPassBund TINYINT UNSIGNED,
                ibPeChauffBund1 TINYINT UNSIGNED,
                ibPeChauffBund2 TINYINT UNSIGNED,
                ibPeChauffBund3 TINYINT UNSIGNED,
                ibRsChauffBund TINYINT UNSIGNED,
                ibPePassBund TINYINT UNSIGNED,
                ibRsPassBund TINYINT UNSIGNED,
                studentDorm TINYINT UNSIGNED,
                studentRent TINYINT UNSIGNED,
                activityString VARCHAR(255),
                transitPass TINYINT UNSIGNED
            );  ''')
        self.database.cursor.executemany(
            f'INSERT INTO persons VALUES({", ".join("?"*39)});', persons)
        self.database.cursor.execute(
            'CREATE UNIQUE INDEX persons_person ON persons(hhid, pnum)')
        self.database.connection.commit()


    def parse(self, trips_file, households_file, persons_file):
        log.info('Parsing households.')
        self.parse_households(households_file)
        log.info('Parsing persons.')
        self.parse_persons(persons_file)
        log.info('Parsing trips.')
        self.parse_trips(trips_file)


    def fetch_count(self, table):
        self.database.cursor.execute(f'SELECT COUNT(*) FROM {table};')
        return self.database.cursor.fetchall()[0][0]


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
                activitity_id INT UNSIGNED,
                agent_id MEDIUMINT UNSIGNED,
                agent_idx TINYINT UNSIGNED,
                type VARCHAR(255),
                apn VARCHAR(255),
                `group` MEDIUMINT UNSIGNED,
                start MEDUMINT UNSIGNED,
                end MEDIUMINT UNSIGNED,
                duration UNSIGNED
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
            subpopulation = Subpopulation()
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

        
    def sample(self, transit=True, party=True, bike=True, 
            walk=True, sample=1, count=0):
        self.database.cursor.execute(f'''
            
        ''')
        




    def validate(self):
        log.info('Validating home APN assignment consistency.')
        self.database.cursor.execute('''
            SELECT
                agents.household_id AS household_id,
                COUNT(DISTINCT apn) AS freq
            FROM activities
            INNER JOIN agents
            USING(agent_id)
            WHERE type = 'home'
            GROUP BY household_id; ''')
        result = self.database.cursor.fetchall()
        valid = all(household[1] == 1 for household in result)
        assert valid, 'Multiple apns used per household for home.'

        log.info('All validationtests passed.')

        
        

