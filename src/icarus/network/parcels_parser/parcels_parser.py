
import shapefile

from icarus.network.parcels_parser.database import ParcelDatabseHandle
from icarus.util.print import Printer as pr

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

        pr.print('Creating temporary tables.', time=True)
        self.database.create_temp()

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

        pr.print('Merging tables and dropping temporaries.', time=True)
        self.database.create_all_idxs('temp_residences')
        self.database.create_all_idxs('temp_commerces')
        self.database.drop_table('commerces')
        self.database.drop_table('residences')
        self.database.join_com_parcels()
        self.database.join_res_parcels()
        self.database.drop_table('temp_residences')
        self.database.drop_table('temp_commerces')

        pr.print('Parcel data parsing complete.', time=True)
