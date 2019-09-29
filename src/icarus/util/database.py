
import MySQLdb
import warnings

from icarus.util.print import Printer as pr

# warnings.filterwarnings('ignore', category=MySQLdb._exceptions.Warning)

class DatabaseHandle:
    def __init__(self, params=None, database=None):
        if type(database) is DatabaseHandle:
            self = database
        elif type(params) is dict:
            keys = ('user', 'password', 'db', 'host', 'unix_socket')
            login = {key:params[key] for key in keys if key in params}
            try:
                self.connection = MySQLdb.connect(**login)
                self.cursor = self.connection.cursor()
                self.user = params['user']
                self.host = params['host']
                self.db = params['db']
                self.tables = params['tables'] if 'tables' in params else {}
            except Exception as err:
                raise err

    def drop_table(self, table):
        query = f'DROP TABLE IF EXISTS {self.db}.{table}'
        self.cursor.execute(query)
        self.connection.commit()

    def create_table(self, table):
        table_data = self.tables[table]
        sql_schema = (', ').join(table_data['schema'])
        query = f'DROP TABLE IF EXISTS {self.db}.{table}'
        self.cursor.execute(query)
        self.connection.commit()
        query = f'CREATE TABLE {self.db}.{table} ({sql_schema})'
        self.cursor.execute(query)
        self.connection.commit()

    def create_index(self, table, name):
        columns = (', ').join(self.tables[table]['indexes'][name])
        query = f'''
            CREATE INDEX {name}
            ON {self.db}.{table} ({columns})'''
        self.cursor.execute(query)
        self.connection.commit()

    def create_primary_idx(self, table):
        cols = ','.join(self.tables[table]['primary_idx'])
        query = f'''
            ALTER TABLE {self.db}.{table}
            ADD PRIMARY KEY ({cols}) '''
        self.cursor.execute(query)
        self.connection.commit()

    def create_hash_idx(self, table, name):
        cols = ', '.join(self.tables[table]['hash_idxs'][name])
        query = f'''
            CREATE INDEX {name} USING HASH
            ON {self.db}.{table} ({cols})'''
        self.cursor.execute(query)
        self.connection.commit()        

    def create_btree_idx(self, table, name):
        cols = ', '.join(self.tables[table]['btree_idxs'][name])
        query = f'''
            CREATE INDEX {name}
            ON {self.db}.{table} ({cols})'''
        self.cursor.execute(query)
        self.connection.commit()   
    
    def create_spatial_idx(self, table, name):
        cols = ', '.join(self.tables[table]['spatial_idxs'][name])
        query = f'''
            CREATE SPATIAL INDEX {name}
            ON {self.db}.{table} ({cols})'''
        self.cursor.execute(query)
        self.connection.commit()
    
    def create_all_idxs(self, table, silent=False):
        tbl_data = self.tables[table]
        if 'primary_idx' in tbl_data and len(tbl_data['primary_idx']):
            if not silent:
                pr.print(f'Creating primary index on table "{table}".', time=True)
            self.create_primary_idx(table)
        if 'spatial_idxs' in tbl_data:
            for idx in tbl_data['spatial_idxs']:
                if not silent:
                    pr.print(f'Creating spatial index "{idx}" on table "{table}".',
                        time=True)
                self.create_spatial_idx(table, idx)
        if 'hash_idxs' in tbl_data:
            for idx in tbl_data['hash_idxs']:
                if not silent:
                    pr.print(f'Creating hash index "{idx}" on table "{table}".',
                        time=True)
                self.create_hash_idx(table, idx)
        if 'btree_idxs' in tbl_data:
            for idx in tbl_data['btree_idxs']:
                if not silent:
                    pr.print(f'Creating btree index "{idx}" on table "{table}".',
                        time=True)
                self.create_btree_idx(table, idx)

    def write_rows(self, data, table):
        s_strs = ', '.join(['%s'] * len(self.tables[table]['schema']))
        query = f''' 
            INSERT INTO {self.db}.{table}
            VALUES ({s_strs}) '''
        self.cursor.executemany(query, data)
        self.connection.commit()

    def write_geom_rows(self, data, table, geo=0, srid=2223):
        s_strs = ', '.join(['%s'] * (len(self.tables[table]['schema']) - geo))
        s_strs += f', ST_GEOMFROMTEXT(%s, {srid})' * geo
        query = f''' 
            INSERT INTO {self.db}.{table}
            VALUES ({s_strs}) '''
        self.cursor.executemany(query, data)
        self.connection.commit()
