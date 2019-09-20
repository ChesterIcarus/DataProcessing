
import os
import sys
import shapefile
import json
from getpass import getpass
from argparse import ArgumentParser

if __name__ == '__main__':
    sys.path.insert(1, os.path.join(sys.path[0], '../..'))

from network.parcels_parser.parcels_parser_db import ParcelDatabseHandle
from  icarus.util.print import Printer as pr

class ParcelsParser:
    def __init__(self, database):
        self.database = ParcelDatabseHandle(database)

    @staticmethod
    def encode_poly(poly):
        if len(poly) == 0:
            return None
        if poly[0] != poly[-1]:
            poly.append(poly[0])
        return 'POLYGON((' + ','.join(str(pt[0]) + ' ' +
                str(pt[1]) for pt in poly) + '))'

    def parse_parcels(self, shpfile, resfile, comfile, bin_size=100000):
        pr.print('Beginning network parcel data parsing.', time=True)
        pr.print('Fetching parcel shapefile data.', time=True)

        shapes = {}
        parser = shapefile.Reader(shpfile)
        for item in parser:
            if len(item.shape.points):
                shapes[item.record['APN']] = self.encode_poly(item.shape.points)

        pr.print('Parsing residential parcel data.', time=True)
        pr.print('Residential Parcel Parsing Progress', persist=True, replace=True, 
            frmt='bold', progress=0)

        parser = shapefile.Reader(resfile)
        target = len(parser)
        parcels = []
        parcel_id = 0

        for record in parser.iterRecords():
            apn = record['APN']
            if apn in shapes:
                parcels.append((
                    parcel_id,
                    apn,
                    shapes[apn],
                    shapes[apn]))
                parcel_id += 1
            if parcel_id % bin_size == 0 and parcel_id:
                pr.print(f'Pushing {bin_size} parcels to database.', time=True)

                self.database.write_res_parcels(parcels)
                parcels = []

                pr.print('Resuming residential parcel parsing.', time=True)
                pr.print('Residential Parcel Parsing Progress', persist=True, 
                    replace=True, frmt='bold', progress=parcel_id/target)

        pr.print(f'Pushing {parcel_id % bin_size} parcels to database.', time=True)

        self.database.write_res_parcels(parcels)

        pr.print('Residential Parcel Parsing Progress', persist=True, 
            replace=True, frmt='bold', progress=1)
        pr.push()
        pr.print('Residential parcel data parsing complete.', time=True)
        pr.print('Parsing commercial parcel data.', time =True)
        pr.print('Commercial Parcel Parsing Progress', persist=True, 
            replace=True, frmt='bold', progress=0)

        parser = shapefile.Reader(comfile)
        target = len(parser)
        parcels = []
        parcel_id = 0

        for record in parser.iterRecords():
            apn = record['APN']
            if apn in shapes:
                parcels.append((
                    parcel_id,
                    apn,
                    shapes[apn],
                    shapes[apn]))
                parcel_id += 1
            if parcel_id % bin_size == 0 and parcel_id:
                pr.print(f'Pushing {bin_size} parcels to database.', time=True)

                self.database.write_com_parcels(parcels)
                parcels = []

                pr.print(f'Resuming commercial parcel parsing.', time=True)
                pr.print('Commercial Parcel Parsing Progress', persist=True, 
                    replace=True, frmt='bold', progress=parcel_id/target)

        pr.print(f'Pushing {parcel_id % bin_size} parcels to database.', time=True)

        self.database.write_com_parcels(parcels)

        pr.print('Commercial Parcel Parsing Progress', persist=True, 
            replace=True, frmt='bold', progress=1)
        pr.push()
        pr.print('Commercial parcel data parsing complete.', time=True)
        pr.print('Parcel data parsing complete.', time=True)

    def cleanup(self):
        pr.print('Creating temporary indexes for join.', time=True)
        self.database.create_all_idxs('com_parcels')
        self.database.create_all_idxs('res_parcels')

        pr.print('Joining on MAZs and generating new tables.', time=True)
        self.database.drop_table('commerces')
        self.database.join_com_parcels()
        self.database.drop_table('residences')
        self.database.join_res_parcels()

        pr.print('Dropping original unjoined tables.', time=True)
        self.database.drop_table('com_parcels')
        self.database.drop_table('res_parcels')


if __name__ == '__main__':
    cmdline = ArgumentParser(prog='AgentsParser',
        description='Parse ABM agents csv file into table in a SQL database.')
    cmdline.add_argument('--config', type=str,  dest='config',
        default=(os.path.dirname(os.path.abspath(__file__)) + '/config.json'),
        help=('Specify a config file location; default is "config.json" in '
            'the current working directory.'), nargs=1)
    args = cmdline.parse_args()

    try:
        with open(args.config) as handle:
            params = json.load(handle)['WORKSTATION']
        database = params['database']
        database['password'] = getpass(
            f'SQL password for {database["user"]}@localhost: ')

        parser = ParcelsParser(database)

        if not params['resume']:
            for table in database['tables'].keys():
                parser.database.create_table(table)
        
        parser.parse_parcels(params['shape_file'], params['residence_file'],
            params['commerce_file'])

        parser.cleanup()
        
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