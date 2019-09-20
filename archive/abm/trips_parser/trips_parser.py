
import csv
import json
import os
import sys

from argparse import ArgumentParser
from getpass import getpass

if __name__ == '__main__':
    sys.path.insert(1, os.path.join(sys.path[0], '../..'))

from abm.trips_parser.trips_parser_db import TripsParserDatabaseHandle
from  icarus.util.print import Printer as pr


class TripsParser:
    def __init__(self, database, encoding):
        self.database = TripsParserDatabaseHandle(database)
        self.encoding = encoding

    @staticmethod
    def decode_list(string):
        return [int(num) for num in string[1:-1].replace(' ', '').split(',')]

    def parse_trips(self, filepath, bin_size=1000000, resume=False):
        pr.print(f'Beginning ABM trips parsing from {filepath}.', time=True)
        pr.print(f'Loading process metadata and fetching reference data.', time=True)

        target = sum(1 for l in open(filepath, 'r')) - 1
        tripsfile = open(filepath, 'r', newline='')
        parser = csv.reader(tripsfile, delimiter=',', quotechar='"')
        top = next(parser)
        cols = {key: val for key, val in zip(top, range(len(top)))}

        agents = self.database.fetch_agents()

        trips = []
        trip_id = 0

        if resume:
            pr.print('Identifying parsing resuming location.', time=True)
            offset = self.database.count_trips() - 1
            pr.print(f'Moving to resume location {offset}.', time=True)
            while trip_id < offset:
                next(parser)
                trip_id += 1

        pr.print('Starting trips parsing.', time=True)
        pr.print('Trip Parsing Progress', persist=True, replace=True, 
            frmt='bold', progress=trip_id/target)
        
        for trip in parser:
            hhid = int(trip[cols['hhid']])
            pnum = int(trip[cols['pnum']])
            trips.append((
                trip_id,
                hhid,
                int(trip[cols['uniqueid']]) - 1,
                agents[f'{hhid}-{pnum - 1}'],
                int(trip[cols['personTripNum']]) - 1,
                int(trip[cols['jointTripNum']]),
                int(trip[cols['mode']]),
                int(trip[cols['origPurp']]),
                int(trip[cols['destPurp']]),
                int(trip[cols['origMaz']]),
                int(trip[cols['destMaz']]),
                int(trip[cols['prelimDepartInterval']]),
                int(float(trip[cols['finalDepartMinute']])*60),
                int(trip[cols['prelimArriveInterval']]),
                int(float(trip[cols['finalArriveMinute']])*60),
                int(float(trip[cols['finalTravelMinutes']])*60),
                int(float(trip[cols['activityMinutesAtDest']]))))
            trip_id += 1

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
    cmdline = ArgumentParser(prog='AgentsParser',
        description='Parse ABM agents CSV file into table in a SQL database.')
    cmdline.add_argument('--config', type=str,  dest='config',
        default=(os.path.dirname(os.path.abspath(__file__)) + '/config.json'),
        help=('Specify a config file location; default is "config.json" in '
            'the current working directory.'), nargs=1)
    args = cmdline.parse_args()

    try:
        with open(args.config) as handle:
            params = json.load(handle)['WORKSTATION']
        database = params['database']
        encoding = params['encoding']
        database['password'] = getpass(
            f'SQL password for {database["user"]}@localhost: ')

        parser = TripsParser(database, encoding)

        if not params['resume']:
            for table in database['tables'].keys():
                parser.database.create_table(table)
        
        parser.parse_trips(params['sourcepath'], resume=params['resume'])
        
        if params['create_indexes']:
            pr.print('Beginning index creation on generated tables.', time=True)
            for table in database['tables']:
                parser.database.create_all_idxs(table)
            pr.print('Index creation complete.', time=True)

    except FileNotFoundError as err:
        print(f'Config file {args.config} not found.')
        quit()
    except json.JSONDecodeError as err:
        print(f'Config file {args.config} is not valid JSON.')
        quit()
    except KeyError as err:
        print(f'Config file {args.config} is not valid config file.')
        quit()
    except Exception as err:
        raise(err)