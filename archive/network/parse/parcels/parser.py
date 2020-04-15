
import shapefile

from icarus.network.parse.parcels.database import ParcelDatabse
from icarus.util.print import PrintUtil as pr
from icarus.util.config import ConfigUtil

class ParcelsParser:
    def __init__(self, database):
        self.database = ParcelDatabse(database)

    @staticmethod
    def encode_poly(poly):
        if len(poly) == 0:
            return None
        if poly[0] != poly[-1]:
            poly.append(poly[0])
        return 'POLYGON((' + ','.join(str(pt[0]) + ' ' +
                str(pt[1]) for pt in poly) + '))'

    @classmethod
    def validate_config(self, configpath, specspath):
        config = ConfigUtil.load_config(configpath)
        specs = ConfigUtil.load_specs(specspath)
        config = ConfigUtil.verify_config(specs, config)

        return config

    def run(self, config):
        pr.print('Prallocating process files and tables.', time=True)
        force = config['run']['force']
        bin_size = config['run']['bin_size']
        self.database.create_temp()
        self.create_tables(self.database.tables, force=force)

        pr.print('Parsing parcel shapefile data.', time=True)
        shapes = {}
        parser = shapefile.Reader(config['run']['shapefile_file'])
        for item in parser:
            if len(item.shape.points):
                shapes[item.record['APN']] = self.encode_poly(item.shape.points)

        pr.print('Parsing residential parcel data.', time=True)

        parser = shapefile.Reader(config['run']['residence_file'])
        parcels = []
        parcel_id = 0
        n = 1

        for record in parser.iterRecords():
            apn = record['APN']
            if apn in shapes:
                parcels.append((
                    parcel_id,
                    apn,
                    shapes[apn],
                    shapes[apn]))
                parcel_id += 1

                if parcel_id % bin_size == 0:
                    self.database.write_residences(parcels)
                    parcels = []

                if parcel_id == n:
                    pr.print(f'Found residencial parcel {n}.', time=True)
                    n <<= 1

        self.database.write_residences(parcels)

        if parcel_id != (n >> 1):
            pr.print(f'Found residencial parcel {n}.', time=True)
            
        pr.print('Residential parcel data parsing complete.', time=True)
        pr.print('Parsing commercial parcel data.', time =True)

        parser = shapefile.Reader(config['run']['commerce_file'])
        parcels = []
        parcel_id = 0
        n = 1

        for record in parser.iterRecords():
            apn = record['APN']
            if apn in shapes:
                parcels.append((
                    parcel_id,
                    apn,
                    shapes[apn],
                    shapes[apn]))
                parcel_id += 1

                if parcel_id % bin_size == 0:
                    self.database.write_commerces(parcels)
                    parcels = []

                if parcel_id == n:
                    pr.print(f'Found residencial parcel {n}.', time=True)
                    n <<= 1

        self.database.write_commerces(parcels)
        
        if parcel_id != (n >> 1):
            pr.print(f'Found residencial parcel {n}.', time=True)

        pr.print('Joining parcel and MAZ data.', time=True)

        self.database.create_all_idxs('temp_residences')
        self.database.create_all_idxs('temp_commerces')
        self.database.drop_table('commerces')
        self.database.drop_table('residences')
        self.database.join_commerces()
        self.database.join_residences()
        self.database.drop_table('temp_residences')
        self.database.drop_table('temp_commerces')
        del self.database.tables['temp_residences']
        del self.database.tables['temp_commerces']

        if config['create_idxs']:
            pr.print('Beginning index creation on generated tables.', time=True)
            for table in self.database.tables:
                self.database.create_all_idxs(table)
            pr.print('Index creation complete.', time=True)

        pr.print('Parcel data parsing complete.', time=True)


    def create_tables(self, *tables, force=False):
        if not force:
            exists = self.database.table_exists(*tables)
            if len(exists):
                exists = '", "'.join(exists)
                cond = pr.print(f'Table{"s" if len(exists) > 1 else ""} '
                    f'"{exists}" already exist in database '
                    f'"{self.database.db}". Drop and continue? [Y/n] ', 
                    inquiry=True, time=True, force=True)
                if not cond:
                    pr.print('User chose to terminate process.', time=True)
                    raise RuntimeError
        for table in tables:
            self.database.create_table(table)
