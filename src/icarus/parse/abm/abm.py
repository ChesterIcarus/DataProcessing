
import csv
import logging as log

from icarus.util.sqlite import SqliteUtil
from icarus.util.file import multiopen, exists


class Abm:
    def __init__(self, database: SqliteUtil):
        self.database = database


    def create_tables(self):
        self.database.drop_table('trips', 'households', 'persons')
        query = '''
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
            );  '''
        self.database.cursor.execute(query)
        query = '''
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
                numNonWorkers TINYINT UNSIGNED,
                numRetired TINYINT UNSIGNED,
                numDrivAgeStuds TINYINT UNSIGNED,
                numPreDrivStuds TINYINT UNSIGNED,
                numPreschool TINYINT UNSIGNED,
                hhIncomeDollar MEDIUMINT UNSIGNED,
                hhNumAutos TINYINT UNSIGNED,
                dwellingType TINYINT UNSIGNED,
                ifAvHousehold TINYINT UNSIGED
            );  '''
        self.database.cursor.execute(query)
        query = '''
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
            );  '''
        self.database.cursor.execute(query)
        self.database.connection.commit()


    def create_indexes(self):
        query = '''
            CREATE  INDEX trips_trip ON 
            trips(hhid, pnum, personTripNum); '''
        self.database.cursor.execute(query)
        query = '''
            CREATE INDEX household_households 
            ON households(hhid); '''
        self.database.cursor.execute(query)
        query = '''
            CREATE INDEX persons_person 
            ON persons(hhid, pnum); '''
        self.database.cursor.execute(query)
        self.database.connection.commit()
    

    def load_trips(self, trips_file):
        open_file = multiopen(trips_file, 'rt')
        trips = csv.reader(open_file, delimiter=',', quotechar='"')
        next(trips)

        count = 0
        n = 1

        for trip in trips:
            yield [int(t) for t in trip[0:6]] + [trip[6]] + \
                [int(t) for t in trip[7:15]] + [float(t) for t in trip[15:18]]
            count += 1
            if count == n:
                log.info(f'Parsing trip {count}.')
                n <<= 1
        if count != n << 1:
            log.info(f'Parsing trip {count}.')
        open_file.close()


    def load_households(self, households_file):
        open_file = multiopen(households_file, 'rt')
        households = csv.reader(open_file, delimiter=',', quotechar='"')
        next(households)

        count = 0
        n = 1

        for household in households:
            yield [int(h) for h in household[0:2]] + [float(household[2])] + \
                [int(h) for h in household[3:18]]
            count += 1
            if count == n:
                log.info(f'Parsing household {count}.')
                n <<= 1
        if count != n << 1:
            log.info(f'Parsing household {count}.')
        open_file.close()


    def load_persons(self, persons_file):
        open_file = multiopen(persons_file, 'rt')
        persons = csv.reader(open_file, delimiter=',', quotechar='"')
        next(persons)

        count = 0
        n = 1

        for person in persons:
            yield [int(p) for p in person[0:2]] + [float(person[2])] + \
                [int(p) for p in person[3:18]] + [person[18]] + \
                [int(p) for p in person[19:37]] + [person[37]] + [int(person[38])]
            count += 1
            if count == n:
                log.info(f'Parsing person {count}.')
                n <<= 1
        if count != n << 1:
            log.info(f'Parsing person {count}.')
        open_file.close()

    
    def ready(self, trips_file, households_file, persons_file):
        ready = True
        abm_files = (trips_file, households_file, persons_file)
        for abm_file in abm_files:
            if not exists(trips_file):
                log.warn(f'Could not find file {abm_file}.')
                ready = False
        return ready

    
    def complete(self):
        tables = ('households', 'persons', 'trips')
        return len(self.database.table_exists(*tables)) == len(tables)


    def parse(self, trips_file, households_file, persons_file):
        log.info('Allocating tables for households, persons and trips.')
        self.create_tables()

        log.info('Parsing households.')
        households = self.load_households(households_file)
        self.database.insert_values('households', households, 18)
        self.database.connection.commit()
        del households

        log.info('Parsing persons.')
        persons = self.load_persons(persons_file)
        self.database.insert_values('persons', persons, 39)
        self.database.connection.commit()
        del persons

        log.info('Parsing trips.')
        trips = self.load_trips(trips_file)
        self.database.insert_values('trips', trips, 18)
        self.database.connection.commit()
        del trips

        log.info('Creating indexes on new tables.')
        self.create_indexes()
