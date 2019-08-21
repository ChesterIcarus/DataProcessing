from typing import List, Dict, Tuple
from warnings import warn
import MySQLdb as sql
import MySQLdb.connections as connections

from util.print_util import Printer as pr

class DatabaseHandle:
    connection = connections.Connection
    cursor = connections.cursors.Cursor
    user: str = None
    host: str = None
    db: str = None
    tables: Dict[str, Dict] = None

    def __init__(self, params: Dict[str, str] = None, handle=None):
        if type(handle) is DatabaseHandle:
            self = handle

        elif isinstance(params, dict):
            keys = ('user', 'password', 'db', 'host', 'unix_socket')
            login = {key:params[key] for key in keys if key in params}
            try:
                self.connection = sql.connect(**login)
                self.cursor = self.connection.cursor()
                self.user = params['user']
                self.host = params['host']
                if 'db' in params:
                    self.db = params['db']
            except Exception:
                connection: sql.connections.Connection
                connection = sql.connect(**login)
                cursor = connection.cursor()
                cursor.execute(f'CREATE DATABASE {params["db"]}')
                connection.commit()
                cursor.close()
                connection.close()
                self.connection = sql.connect(**login)
                self.cursor = self.connection.cursor()
                self.user = params['user']
                self.host = params['host']
                self.db = params['db']

        else:
            self.user = None
            self.host = None
            self.db = None
            self.cursor = None
            self.connection = None
            warn('No valid database passed, DatabaseHandle initialized without connection')
        if 'tables' in params:
            self.tables = params['tables']
        else:
            self.tables = None

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

    def create_spatial_index(self, table, name):
        cols = ', '.join(self.tables[table]['spatial_indexes'][name])
        query = f'''
            CREATE SPATIAL INDEX {name}
            ON {self.db}.{table} ({cols}) '''
        self.cursor.execute(query)
        self.connection.commit()

    def create_hash_idx(self, table, name):
        cols = ', '.join(self.tables[table]['hash_idxs'][name])
        query = f'''
            CREATE INDEX USING HASH {name}
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
    
    def create_all_idxs(self, table):
        tbl_data = self.tables[table]
        if 'spatial_idxs' in tbl_data:
            for idx in tbl_data['spatial_idxs']:
                self.create_spatial_idx(table, idx)
        if 'hash_idxs' in tbl_data:
            for idx in tbl_data['hash_idxs']:
                self.create_hash_idx(table, idx)
        if 'btree_idxs' in tbl_data:
            for idx in tbl_data['btree_idxs']:
                self.create_btree_idx(table, idx)


    def alter_add_composite_PK(self, table):
        formed_index_cols = (', ').join(self.tables[table]['comp_PK'])
        query = f'''
            ALTER TABLE {self.db}.{table}
            ADD PRIMARY KEY ({formed_index_cols}) '''
        self.cursor.execute(query)
        self.connection.commit()

    def write_rows(self, data, table):
        s_strs = ', '.join(['%s'] * len(self.tables[table]['schema']))
        query = f''' 
            INSERT INTO {self.db}.{table}
            VALUES ({s_strs}) '''
        self.cursor.executemany(query, data)
        self.connection.commit()

    def write_geom_rows(self, data, table, geo=0):
        s_strs = ', '.join(['%s'] * (len(self.tables[table]['schema']) - geo))
        s_strs += ', ST_GEOMFROMTEXT(%s, 2223)' * geo
        query = f''' 
            INSERT INTO {self.db}.{table}
            VALUES ({s_strs}) '''
        self.cursor.executemany(query, data)
        self.connection.commit()
