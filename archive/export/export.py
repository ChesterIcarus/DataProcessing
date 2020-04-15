
import subprocess
import os
import logging

from getpass import getpass

from argparse import ArgumentParser

from icarus.util.database import DatabaseUtil
from icarus.util.filesys import FilesysUtil

class SqlExporter(DatabaseUtil):
    cols = {
        'agents': ['agent_id', 'household_id', 'household_idx', 'uses_vehicle',
            'uses_walk', 'uses_bike', 'uses_transit', 'uses_party', 'input_size', 
            'output_size', 'exposure'],
        'activities': ['agent_id', 'agent_idx', 'type', 'maz', 
            'apn', 'x', 'y', 'input_start', 'input_end', 'input_duration', 
            'output_start', 'output_end', 'output_duration', 'exposure'],
        'routes': ['agent_id', 'agent_idx', 'shared' 'mode', 'start_apn', 
            'end_apn','input_start', 'input_end', 'input_duration', 
            'output_start','output_end', 'output_duration', 'exposure'] }

    def export(self, input_db, output_db, export_dir):
        files = ['agents.csv', 'activities.csv', 'routes.csv']
        targets = [os.path.join(export_dir, f) for f in files]
        sources = [os.path.join('/tmp/mysql', f) for f in files]
        cols = [
            ', '.join(self.cols['agents']),
            ', '.join(self.cols['activities']),
            ', '.join(self.cols['routes'])  ]

        for t in targets:
            if FilesysUtil.file_exists(t):
                raise FileExistsError

        subprocess.run(['rm', '-f', *sources], shell=False)
        print('Exporting agents.')
        self.export_agents(input_db, output_db)
        print('Exporting activities.')
        self.export_activities(input_db, output_db)
        print('Exporting routes.')
        self.export_routes(input_db, output_db)

        print('Copying and joining.')
        for t, c in zip(targets, cols):
            subprocess.run(f'echo "{c}" > {t}', shell=True)
        
        for s, t in zip(sources, targets):
            subprocess.run(f'cat {s} >> {t}', shell=True)

        print('Cleaning up.')
        subprocess.run(['rm', '/tmp/mysql/*'], shell=False)

    def export_agents(self, input_db, output_db):
        query = f'''
            SELECT 
                input.agent_id,
                input.household_id,
                input.household_idx,
                input.uses_vehicle,
                input.uses_walk,
                input.uses_bike,
                input.uses_transit,
                input.uses_party,
                input.size,
                output.size,
                output.exposure
            FROM {input_db}.agents AS input
            INNER JOIN {output_db}.agents AS output
            USING(agent_id)
            INTO OUTFILE "/tmp/mysql/agents.csv"
            FIELDS OPTIONALLY ENCLOSED BY '"'
                TERMINATED BY ','
                ESCAPED BY '\\\\'
            LINES TERMINATED BY '\n'    '''
        self.cursor.execute(query)
        self.connection.commit()

    
    def export_activities(self, input_db, output_db):
        query = f'''
            SELECT
                input.agent_id,
                input.agent_idx,
                output.type,
                input.maz,
                input.apn,
                ST_X(input_apn.center),
                ST_Y(input_apn.center),
                input.start,
                input.end,
                input.duration,
                output.start,
                output.end,
                output.duration,
                output.exposure
            FROM {input_db}.activities AS input
            INNER JOIN {output_db}.agents
            USING(agent_id)
            INNER JOIN network.parcels AS input_apn
            USING(apn)
            LEFT JOIN {output_db}.activities AS output
            USING(agent_id, agent_idx)
            INTO OUTFILE "/tmp/mysql/activities.csv"
            FIELDS OPTIONALLY ENCLOSED BY '"'
                TERMINATED BY ','
                ESCAPED BY '\\\\'
            LINES TERMINATED BY '\n'    '''
        self.cursor.execute(query)
        self.connection.commit()


    def export_routes(self, input_db, output_db):
        query = f'''
            SELECT
                input.agent_id,
                input.agent_idx,
                input.shared,
                output.mode,
                start_act.apn,
                end_act.apn,
                input.start,
                input.end,
                input.duration,
                output.start,
                output.end,
                output.duration,
                output.exposure
            FROM {input_db}.routes AS input
            INNER JOIN {output_db}.agents
            USING(agent_id)
            INNER JOIN {input_db}.activities AS start_act
            USING (agent_id, agent_idx)
            INNER JOIN {input_db}.activities AS end_act
            ON input.agent_id = end_act.agent_id
            AND input.agent_idx + 1= end_act.agent_idx
            LEFT JOIN {output_db}.routes AS output
            USING(agent_id, agent_idx)
            INTO OUTFILE "/tmp/mysql/routes.csv"
            FIELDS OPTIONALLY ENCLOSED BY '"'
                TERMINATED BY ','
                ESCAPED BY '\\\\'
            LINES TERMINATED BY '\n'    '''
        self.cursor.execute(query)
        self.connection.commit()


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--database', type=str, nargs=2, required=True)
    parser.add_argument('--dir', type=str, default=os.getcwd())
    parser.add_argument('--user', type=str, required=True)
    parser.add_argument('--password', type=str, default=None)
    args = parser.parse_args()

    if args.password is None:
        args.password = getpass(f'sql password for {args.user}@localhost:')

    params = {
        'password': args.password,
        'user': args.user,
        'host': 'localhost',
        'unix_socket': '/home/mysql/mysql.sock',
        'db': 'network'
    }

    exporter = SqlExporter(params=params)
    exporter.export(*args.database, args.dir)
