
import csv
import json
import os
import sys
from getpass import getpass

if __name__ == '__main__':
    sys.path.insert(1, os.path.join(sys.path[0], '../..'))

from abm.trips_parser.trips_parser_db import TripsParserDatabaseHandle
from util.print_util import Printer as pr


class TripsParser:
    def __init__(self, database, encoding):
        self.database = TripsParserDatabaseHandle(database)
        self.encoding = encoding

    @staticmethod
    def decode_list(string):
        return [int(num) for num in string[1:-1].replace(' ', '').split(',')]

    def parse_trips(self, filepath, bin_size=1000000, resume=False):
        pr.print(f'Beginning ABM trips parsing from {filepath}.', time=True)
        pr.print(f'Loading files and fetching reference data.', time=True)

        target = sum(1 for l in open(filepath, 'r')) - 1
        tripsfile = open(filepath, 'r', newline='')
        parser = csv.reader(tripsfile, delimiter=',', quotechar='"')
        top = next(parser)
        cols = {key: val for key, val in zip(top, range(len(top)))}

        agents = self.database.fetch_agents()

        trips = []
        groups = {}

        last_household = 0
        trip_id = 0
        trip_index = 0

        if resume:
            pr.print('Identifying parsing resuming location.', time=True)
            max_trip, max_hhid = self.database.trips_info()
            pr.print('Moving to resume location.', time=True)
            for trip in trips:
                if int(trip[cols['hhid']]) == max_hhid:
                    group = int(trip[cols['jointTripNum']])
                    if group and group not in groups:
                        groups[group] = trip_index
                    else:
                        trip_index += 1
                if trip_id == max_trip:
                    last_household = int(trip[cols['hhid']])
                    break
                trip_id += 1

        pr.print('Trip Parsing Progress', persist=True, replace=True, 
            frmt='bold', progress=trip_id/target)
        for trip in parser:
            active_household = int(trip[cols['hhid']])
            agent = int(trip[cols['pnum']])
            group = int(trip[cols['jointTripNum']])
            if last_household != active_household:
                trip_index = 0
                groups = {}
            if group and group not in groups:
                groups[group] = trip_index
                trip_index += 1
            trips.append((
                trip_id,
                active_household,
                trip_index if not group else groups[group],
                agents[f'{active_household}-{agent}'],
                int(trip[cols['personTripNum']]),
                int(trip[cols['mode']]),
                int(trip[cols['origPurp']]),
                int(trip[cols['destPurp']]),
                int(trip[cols['origMaz']]),
                int(trip[cols['destMaz']]),
                int(float(trip[cols['finalDepartMinute']])*60),
                int(float(trip[cols['finalArriveMinute']])*60)))        
            trip_id += 1
            trip_index += 1 if not group else 0
            last_household = active_household

            if trip_id % bin_size == 0:
                pr.print(f'Pushing {bin_size} trips to the database.', time=True)
                self.database.push_trips(trips)
                pr.print('Trip Parsing Progress', persist=True, replace=True,
                    frmt='bold', progress=trip_id/target)
                pr.print(f'Resuming trips parsing.', time=True)
                trips = []

        pr.print(f'Pushing {trip_id % bin_size} trips to the database.', time=True)
        self.database.push_trips(trips)
        pr.print('Trip Parsing Progress', persist=True, replace=True, 
            frmt='bold', progress=1)
        pr.push()
        pr.print('ABM trip parsing complete.', time=True)
        tripsfile.close()

if __name__ == '__main__':
    if len(sys.argv) > 2:
        configpath = sys.argv[1]
    else:
        configpath = os.path.dirname(os.path.abspath(__file__)) + '/config.json'
    try:
        with open(configpath) as handle:
            params = json.load(handle)['WORKSTATION']
        database = params['database']
        encoding = params['encoding']
        database['password'] = getpass(
            f'Password for {database["user"]}@localhost: ')
        parser = TripsParser(database, encoding)
        if not params['resume']:
            for table in database['tables'].keys():
                parser.database.create_table(table)
        
        parser.parse_trips(params['sourcepath'], resume=params['resume'])
        
        if params['create_indexes']:
            pr.print('Beginning index creation on generated tables.', time=True)
            for tbl, table in database['tables'].items():
                for idx, index in table['indexes'].items():
                    pr.print(f'Creating index "{idx}" on table "{tbl}".', time=True)
                    parser.database.create_index(tbl, idx)
            pr.print('Index creation complete.', time=True)
    except FileNotFoundError as err:
        print(f'Config file {configpath} not found.')
        quit()
    except json.JSONDecodeError as err:
        print(f'Config file {configpath} is not valid JSON.')
        quit()
    except KeyError as err:
        print(f'Config file {configpath} is not valid config file.')
        quit()
    except Exception as err:
        raise(err)