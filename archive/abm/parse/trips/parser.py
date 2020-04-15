
import csv

from getpass import getpass
from argparse import ArgumentParser

from icarus.abm.parse.trips.database import TripsParserDatabase
from icarus.util.print import PrintUtil as pr
from icarus.util.config import ConfigUtil


class TripsParser:
    def __init__(self, database):
        self.database = TripsParserDatabase(database)


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


    @classmethod
    def validate_config(self, configpath, specspath):
        config = ConfigUtil.load_config(configpath)
        specs = ConfigUtil.load_specs(specspath)
        config = ConfigUtil.verify_config(specs, config)

        return config


    def run(self, config):
        pr.print('Prallocating process files and tables.', time=True)
        force = config['run']['force']
        self.create_tables('trips', 'temp_trips', force=force)

        pr.print('Creating temporary tables.', time=True)
        self.database.create_temp()

        pr.print(f'Loading process metadata and resources.', time=True)
        trips_path = config['run']['trips_file']
        bin_size = config['run']['bin_size']

        target = sum(1 for l in open(trips_path, 'r')) - 1
        tripsfile = open(trips_path, 'r', newline='')
        parser = csv.reader(tripsfile, delimiter=',', quotechar='"')
        top = next(parser)
        cols = {key: val for key, val in zip(top, range(len(top)))}

        trips = []
        parties = {}
        trip_id = 0
        party_id = 1
        
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

                pr.print('Resuming CSV file parsing.', time=True)
                pr.print('Trips Parsing Progress', persist=True, replace=True,
                    frmt='bold', progress=trip_id/target)
                trips = []

        pr.print(f'Pushing {trip_id % bin_size} trips to the database.', time=True)
        self.database.write_trips(trips)

        pr.print('Trips Parsing Progress', persist=True, replace=True,
            frmt='bold', progress=1)
        pr.push()
        pr.print('ABM trip data parsing complete.', time=True)

        pr.print('Merging tables and dropping temporaries.', time=True)
        pr.silence()
        self.database.drop_table('trips')
        self.database.create_all_idxs('temp_trips')
        self.database.join_trips()
        self.database.drop_table('temp_trips')
        del self.database.tables['temp_trips']
        pr.unsilence()

        if config['run']['create_idxs']:
            pr.print(f'Creating all indexes in database '
                f'{self.database.db}.', time=True)
            self.create_idxs()
            pr.print(f'Index creating complete.', time=True)


    def create_idxs(self):
        for tbl in self.database.tables:
            self.database.create_all_idxs(tbl)


    def create_tables(self, *tables, force=False):
        if not force:
            exists = self.database.table_exists(tables)
            if len(exists):
                cond = pr.print(f'Tables "{exists}" already exist in database '
                    f'"{self.database.db}". Drop and continue? [Y/n] ', 
                    inquiry=True, time=True, force=True)
                if cond:
                    pr.print('User chose to terminate process.')
                    raise RuntimeError
        for table in tables:
            self.database.drop_table(table)
