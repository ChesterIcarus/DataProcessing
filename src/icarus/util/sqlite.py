
import sqlite3
import re
import os

from icarus.util.iter import chunk


class SqliteUtil:
    def __init__(self, database, readonly=False, timeout=30):
        self.name = database
        self.timeout = timeout
        self.readonly = readonly
        self.connection = None
        self.cursor = None
        self.open(timeout)


    def open(self, timeout):
        if self.connection is not None:
            self.close()
        if self.readonly:
            path = os.path.abspath(self.name)
            uri = f'file:{path}?mode=ro'
            self.connection = sqlite3.connect(uri, uri=True, timeout=timeout)
        else: 
            self.connection = sqlite3.connect(self.name, timeout=timeout)
        self.cursor = self.connection.cursor()


    def close(self):
        self.connection.close()
        self.connection = None
        self.cursor = None


    def count_rows(self, table):
        self.cursor.execute(f'SELECT COUNT(*) from {table};')
        return self.cursor.fetchall()[0][0]


    def count_null(self, table, col):
        query = f'''
            SELECT
                CASE 
                    WHEN {col} IS NULL 
                    THEN 0 ELSE 1 
                    END AS valid,
                COUNT(*) AS freq
            FROM {table}
            GROUP BY valid;
        '''
        self.cursor.execute(query)
        rows = self.fetch_rows()
        
        null, nnull = 0, 0
        for value, freq in rows:
            if value == 0:
                null = freq
            else:
                nnull = freq

        return null, nnull


    def fetch_rows(self, chunk_size=None, block_size=1000000):
        rows = self.cursor.fetchmany(block_size)
        while len(rows):
            if chunk_size is None:
                for row in rows:
                    yield row
            else:
                for row in chunk(row, chunk_size):
                    yield row    
            rows = self.cursor.fetchmany(block_size)

    
    def fetch_tables(self):
        self.cursor.execute('SELECT name FROM sqlite_master WHERE type="table";')
        tables = self.cursor.fetchall()
        return [table[0] for table in tables]

    
    def drop_temporaries(self):
        tables = self.fetch_tables()
        drop = [table for table in tables if re.match(r'^temp_[0-9]+$', table)]
        self.drop_table(*drop)


    def table_exists(self, *tables):
        exist = self.fetch_tables()
        return tuple(set(exist).intersection(tables))


    def drop_table(self, *tables):
        for table in tables:
            self.cursor.execute(f'DROP TABLE IF EXISTS {table};')


    def drop_index(self, *indexes):
        for index in indexes:
            self.cursor.execute(f'DROP INDEX IF EXISTS {index};')

    
    def insert_values(self, table, values, cols):
        columns = ', '.join('?' * cols)
        query = f'INSERT INTO {table} VALUES({columns});'
        self.cursor.executemany(query, values)

    
    def write_metadata(self, fields = {}, **kwargs):
        exists = bool(len(self.table_exists('metadata')))
        fields = {**fields, **kwargs}

        if not exists:
            query = '''
                CREATE TABLE metadata(
                    field VARCHAR(255),
                    value VARCHAR(255),
                    type VARCHAR(255)
                );
            '''
            self.cursor.execute(query)
        else:
            remove = (f'field = {field}' for field in fields)
            condition = ', OR '.join(remove)
            query = f'DELETE FROM metadata WHERE {condition};'
        
        values = ((key, val, type(val).__name__) for key, val in fields.items())
        self.insert_values('metadata', values, 3)

        query = '''
            CREATE TABLE temp_metadata AS 
            SELECT 
                field,
                value,
                type
            FROM metadata
            ORDER BY field DESC;
        '''
        self.cursor.execute(query)
        self.drop_table('metadata')
        query = 'ALTER TABLE temp_metadata RENAME TO metadata'
        self.cursor.execute(query)

    
    def fetch_metadata(self):
        query = 'SELECT * FROM metadata;'
        self.cursor.execute(query)
        rows = self.fetch_rows()

        metadata = {}
        for field, value, kind in rows:
            if kind == 'str':
                value = str(value)
            elif kind == 'int':
                value = int(value)
            elif kind == 'float':
                value = float(value)
            elif kind == 'bool':
                value = bool(value)
            metadata[field] = value
        
        return metadata


    def get_schema(self, table):
        query = f'''
            SELECT sql 
            FROM sqlite_master 
            WHERE type="tabl"' 
            AND name="{table}";
        '''
        self.cursor.execute(query)
        return self.cursor.fetchall()[0][0]

    
    def copy_schema(self, old_table, new_table):
        query = self.get_schema(old_table)
        self.cursor.execute(query)
