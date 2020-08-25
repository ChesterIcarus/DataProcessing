
import os
import csv
import logging as log

from argparse import ArgumentParser, SUPPRESS

from icarus.util.sqlite import SqliteUtil
from icarus.util.config import ConfigUtil
from icarus.util.file import multiopen, exists
from icarus.util.general import counter


def ready(trips_file: str, households_file: str, persons_file: str):
    ready = True
    abm_files = (trips_file, households_file, persons_file)
    for abm_file in abm_files:
        if not exists(trips_file):
            log.warning(f'Could not open file {abm_file}.')
            ready = False
    return ready


def complete(database: SqliteUtil):
    complete = False
    tables = ('households', 'persons', 'trips')
    present = database.table_exists(*tables)
    for table in present:
        log.warning(f'Table {table} already exists.')
        complete = True
    return complete


def create_tables(database: SqliteUtil):
    database.drop_table('trips', 'households', 'persons')
    query = '''
        CREATE TABLE trips(
            hhid_uniqueid INT UNSIGNED,
            uniqueid SMALLINT UNSIGNED,
            hhid MEDIUMINT UNSIGNED,
            pnum TINYINT UNSIGNED,
            personTripNum TINYINT UNSIGNED,
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
        );
    '''
    database.cursor.execute(query)
    query = '''
        CREATE TABLE households(
            hhid MEDIUMINT UNSIGNED,
            hhidAcrossSample MEDIUMINT UNSIGNED,
            pumsSerialNo FLOAT,
            homeTaz SMALLLINT UNSIGNED,
            homeMaz SMALLINT UNSIGNED,
            hhsize TINYINT UNSIGNED,
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
            ifAvHousehold TINYINT UNSIGNED
        );
    '''
    database.cursor.execute(query)
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
            workPlaceTaz SMALLINT SIGNGED,
            workPlaceMaz SMALLINT SIGNGED,
            schoolType TINYINT UNSIGNED,
            schoolTaz SMALLINT UNSIGNED,
            schoolMaz SMALLINT UNSIGNED,
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
        );
    '''
    database.cursor.execute(query)
    database.connection.commit()


def create_indexes(database: SqliteUtil):
    query = '''
        CREATE  INDEX trips_trip ON 
        trips(hhid, pnum, personTripNum);
    '''
    database.cursor.execute(query)
    query = '''
        CREATE INDEX household_households 
        ON households(hhid);
    '''
    database.cursor.execute(query)
    query = '''
        CREATE INDEX persons_person 
        ON persons(hhid, pnum); 
    '''
    database.cursor.execute(query)
    database.connection.commit()


def load_trips(trips_file: str):
    open_file = multiopen(trips_file, 'rt')
    trips = csv.reader(open_file, delimiter=',', quotechar='"')
    next(trips)
    trips = counter(trips, 'Parsing trip %s.', level=log.DEBUG)

    for trip in trips:
        yield [int(t) for t in trip[0:6]] + [trip[6]] + \
            [int(t) for t in trip[7:15]] + [float(t) for t in trip[15:18]]

    open_file.close()


def load_households(households_file: str):
    open_file = multiopen(households_file, 'rt')
    households = csv.reader(open_file, delimiter=',', quotechar='"')
    next(households)
    households = counter(households, 'Parsing household %s.', level=log.DEBUG)

    for household in households:
        yield [int(h) for h in household[0:2]] + [float(household[2])] + \
            [int(h) for h in household[3:18]]
        
    open_file.close()


def load_persons(persons_file: str):
    open_file = multiopen(persons_file, 'rt')
    persons = csv.reader(open_file, delimiter=',', quotechar='"')
    next(persons)
    persons = counter(persons, 'Loading person %s.', level=log.DEBUG)

    for person in persons:
        yield [int(p) for p in person[0:2]] + [float(person[2])] + \
            [int(p) for p in person[3:18]] + [person[18]] + \
            [int(p) for p in person[19:37]] + [person[37]] + [int(person[38])]
            
    open_file.close()


def build_report(database: SqliteUtil):
    npersons = database.count_rows('persons')
    nhouseholds = database.count_rows('households')
    ntrips = database.count_rows('trips')
    report = '\n'.join((
        'Process Report:',
        'total households parsed: %d' % nhouseholds,
        'total persons parsed:    %d' % npersons,
        'total trips parsed:      %d' % ntrips
    ))
    log.info(report)


def parse_abm(database: SqliteUtil, trips_file: str, households_file: str, 
        persons_file: str):
    log.info('Allocating tables for households, persons and trips.')
    create_tables(database)

    log.info('Parsing households.')
    households = load_households(households_file)
    database.insert_values('households', households, 18)
    database.connection.commit()
    del households

    log.info('Parsing persons.')
    persons = load_persons(persons_file)
    database.insert_values('persons', persons, 39)
    database.connection.commit()
    del persons

    log.info('Parsing trips.')
    trips = load_trips(trips_file)
    database.insert_values('trips', trips, 18)
    database.connection.commit()
    del trips

    log.info('Creating indexes on new tables.')
    create_indexes(database)

    log.info('Building process results.')
    build_report(database)

    log.info('Process complete; exiting.')


def main():
    desc = (
        'Parse the MAG ABM trips, households and persons files into '
        'an SQLite database and build some useful indexes; this data '
        'is copied into tables without any filtering or alteration. '
        'This process requires you have the ABM file locations specified '
        'in the simulation configuration file.'
    )
    parser = ArgumentParser('icarus.parse.abm', description=desc, add_help=False)

    general = parser.add_argument_group('general options')
    general.add_argument('--help', action='help', default=SUPPRESS,
        help='show this help menu and exit process')
    general.add_argument('--dir', type=str, dest='dir', default='.',
        help='path to simulation data; default is current working directory')
    general.add_argument('--log', type=str, dest='log', default=None,
        help='location to save additional logfiles')
    general.add_argument('--level', type=str, dest='level', default='info',
        choices=('notset', 'debug', 'info', 'warning', 'error', 'critical'),
        help='level of verbosity to print log messages')
    general.add_argument('--force', action='store_true', dest='force', 
        default=False, help='skip prompts for deleting files/tables')

    args = parser.parse_args()

    path = lambda x: os.path.abspath(os.path.join(args.dir, x))
    os.makedirs(path('logs'), exist_ok=True)
    homepath = path('')
    logpath = path('logs/parse_abm.log')
    dbpath = path('database.db')
    configpath = path('config.json')

    handlers = []
    handlers.append(log.StreamHandler())
    handlers.append(log.FileHandler(logpath, 'w'))
    if args.log is not None:
        handlers.append(log.FileHandler(args.log, 'w'))
    if args.level == 'debug':
        frmt = '%(asctime)s %(levelname)s %(filename)s:%(lineno)s %(message)s'
    else:
        frmt = '%(asctime)s %(levelname)s %(message)s'
    log.basicConfig(
        format=frmt,
        level=getattr(log, args.level.upper()),
        handlers=handlers
    )

    log.info('Running abm parsing module.')
    log.info(f'Loading data from {homepath}.')
    log.info('Verifying process metadata/conditions.')

    database = SqliteUtil(dbpath)
    config = ConfigUtil.load_config(configpath)

    trips_file = config['population']['trips_file']
    persons_file = config['population']['persons_file']
    households_file = config['population']['households_file']

    if not ready(trips_file, households_file, persons_file):
        log.error('Process dependencies not met; see warnings and '
            'documentation for more details.')
        exit(1)
    if complete(database) and not args.force:
        log.error('Some or all of this process is already complete.')
        log.error('Would you like to continue? [Y/n]')
        if input().lower() not in ('y', 'yes', 'yeet'):
            exit()

    try:
        log.info('Starting population parsing.')
        parse_abm(database, trips_file, households_file, persons_file)
    except:
        log.exception('Critical error while parsing population; '
            'terminating process and exiting.')
        exit(1)


if __name__ == '__main__':
    main()
