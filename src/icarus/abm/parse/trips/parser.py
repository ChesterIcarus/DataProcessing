
import csv

from getpass import getpass
from argparse import ArgumentParser

from icarus.abm.parse.trips.database import TripsParserDatabase
from icarus.util.print import Printer as pr

class TripsParser:
    def __init__(self, database, encoding):
        self.database = TripsParserDatabase(database)
        self.encoding = encoding


    @staticmethod
    def adj_time(time):
        return int(float(time)*60)


    @staticmethod
    def hash_party(party, start):
        agents = party[2:-2].split(',')
        if len(agents) > 1:
            return (start, frozenset(agents))
        else:
            None


    def parse(self, sourcepath, resume=False, bin_size=100000):
        pr.print(f'Beginning AMB trip data parsing from {sourcepath}.', time=True)
        pr.print('Creating temporary tables.', time=True)

        self.database.create_temp()

        pr.print(f'Loading process metadata and resources.', time=True)

        target = sum(1 for l in open(sourcepath, 'r')) - 1
        tripsfile = open(sourcepath, 'r', newline='')
        parser = csv.reader(tripsfile, delimiter=',', quotechar='"')
        top = next(parser)
        cols = {key: val for key, val in zip(top, range(len(top)))}

        trips = []
        parties = {}
        trip_id = 0
        party_id = 1

        if resume:
            pr.print('Finding where we left off last.', time=True)
            offset = self.database.count_trips()
            pr.print(f'Skipping to trip {offset}.', time=True)
            for _ in range(offset):
                next(parser)
        
        pr.print('Starting trips CSV file iteration.', time=True)
        pr.print('Trips Parsing Progress', persist=True, replace=True,
            frmt='bold', progress=trip_id/target)

        household = None

        for trip in parser:
            prev_household = household

            vehicle = int(trip[cols['vehId']])
            household = int(trip[cols['hhid']])
            role = int(trip[cols['jointTripRole']])

            party_hash = self.hash_party(trip[cols['party']], 
                trip[cols['isamAdjDepMin']])

            if prev_household != household:
                parties = {}

            if party_hash is None:
                party = 0
                party_idx = 0
            else:
                if party_hash in parties:
                    party = parties[party_hash][0]
                    party_idx = parties[party_hash][1]
                    parties[party_hash][1] += 1
                else:
                    parties[party_hash] = [party_id, 2]
                    party = party_id
                    party_idx = 1
                    party_id += 1

            trips.append((
                trip_id,
                household,
                int(trip[cols['uniqueid']]),
                int(trip[cols['pnum']]),
                int(trip[cols['personTripNum']]) - 1,
                party,
                party_idx,
                role,
                int(trip[cols['origTaz']]),
                int(trip[cols['origMaz']]),
                int(trip[cols['destTaz']]),
                int(trip[cols['destMaz']]),
                int(trip[cols['origPurp']]),
                int(trip[cols['destPurp']]),
                int(trip[cols['mode']]),
                vehicle if vehicle > 0 else 0,
                self.adj_time(trip[cols['isamAdjDepMin']]) + 16200,
                self.adj_time(trip[cols['isamAdjArrMin']]) + 16200,
                self.adj_time(trip[cols['isamAdjDurMin']])))
            trip_id += 1

            if trip_id % bin_size == 0:
                pr.print(f'Pushing {bin_size} trips to the database.', time=True)
                self.database.write_trips(trips)
                trips = []
                pr.print('Resuming CSV file parsing.', time=True)
                pr.print('Trips Parsing Progress', persist=True, replace=True,
                    frmt='bold', progress=trip_id/target)

        pr.print(f'Pushing {trip_id % bin_size} trips to the database.', time=True)
        self.database.write_trips(trips)

        pr.print('Trips Parsing Progress', persist=True, replace=True,
            frmt='bold', progress=1)
        pr.push()
        pr.print('ABM trip data parsing complete.', time=True)
        pr.print('Merging tables and dropping temporaries.', time=True)
        
        self.database.drop_table('trips')
        self.database.create_all_idxs('temp_trips', silent=True)
        self.database.join_trips()
        self.database.drop_table('temp_trips')
        del self.database.tables['temp_trips']


    def create_idxs(self, silent=False):
        pr.print(f'Creating all indexes in database {self.database.db}.', time=True)
        for tbl in self.database.tables:
            self.database.create_all_idxs(tbl)
        pr.print(f'Index creating complete.', time=True)