
import csv

from icarus.abm.parse.households.database import HouseholdsParserDatabase
from icarus.util.print import PrintUtil as pr
from icarus.util.config import ConfigUtil

class HouseholdsParser:
    def __init__(self, database):
        self.database = HouseholdsParserDatabase(database)


    @classmethod
    def validate_config(self, configpath, specspath):
        config = ConfigUtil.load_config(configpath)
        specs = ConfigUtil.load_specs(specspath)
        config = ConfigUtil.verify_config(specs, config)

        return config
    

    def run(self, config):
        pr.print('Prallocating process files and tables.', time=True)
        force = config['run']['force']
        self.create_tables('households', force=force)

        pr.print(f'Loading process metadata and resources.', time=True)
        households_path = config['run']['households_file']
        bin_size = config['run']['bin_size']

        target = sum(1 for l in open(households_path, 'r')) - 1
        householdsfile = open(households_path, 'r', newline='')
        parser = csv.reader(householdsfile, delimiter=',', quotechar='"')
        top = next(parser)
        cols = {key: val for key, val in zip(top, range(len(top)))}

        households = []
        household_id = 0
        vehicles = []
        vehicle_id = 0

        hhid = 0

        pr.print('Starting households CSV file iteration.', time=True)
        pr.print('Households Parsing Progress', persist=True, replace=True,
            frmt='bold', progress=hhid/target)
        
        for household in parser:
            household_id = int(household[cols['hhid']])
            households.append((
                household_id,
                float(household[cols['pumsSerialNo']]),
                int(household[cols['homeTaz']]),
                int(household[cols['homeMaz']]),
                int(household[cols['hhsize']]),
                int(household[cols['numFtWorkers']]),
                int(household[cols['numPtWorkers']]),
                int(household[cols['numUnivStuds']]),
                int(household[cols['numNonWorkers']]),
                int(household[cols['nunmRetired']]),
                int(household[cols['numDrivAgeStuds']]),
                int(household[cols['numPreDrivStuds']]),
                int(household[cols['numPreshcool']]),
                int(household[cols['hhIncomeDollars']]),
                int(household[cols['hhNumAutos']]),
                int(household[cols['dwellingType']]),
                int(household[cols['ifAvHousehold']])))
            hhid += 1

            for vehicle in range(int(household[cols['hhNumAutos']])):
                vehicles.append((
                    vehicle_id,
                    household_id,
                    vehicle + 1 ))
                vehicle_id += 1

            if hhid % bin_size == 0:
                pr.print(f'Pushing {bin_size} households to database.', time=True)
                self.database.write_households(households)
                self.database.write_vehicles(vehicles)

                pr.print('Resuming household CSV file parsing.', time=True)
                pr.print('Household Parsing Progress', persist=True,
                    replace=True, frmt='bold', progress=hhid/target)
                households = []
                vehicles = []

        pr.print(f'Pushing {hhid % bin_size} households to database.', time=True)
        self.database.write_households(households)

        pr.print('ABM household data parsing complete.', time=True)
        pr.print('Household Parsing Progress', persist=True, replace=True,
            frmt='bold', progress=1)
        pr.push()

        if config['run']['create_idxs']:
            pr.print(f'Creating all indexes in database '
                f'{self.database.db}.', time=True)
            self.create_idxs()
            pr.print(f'Index creating complete.', time=True)


    def create_idxs(self, silent=False):
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
