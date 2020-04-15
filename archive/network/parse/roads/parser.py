
import gzip

from xml.etree.ElementTree import iterparse

from icarus.network.parse.roads.database import RoadParserDatabase
from icarus.util.print import PrintUtil as pr
from icarus.util.config import ConfigUtil

class RoadParser:
    def __init__(self, database):
        self.database = RoadParserDatabase(database)


    @classmethod
    def validate_config(self, configpath, specspath):
        config = ConfigUtil.load_config(configpath)
        specs = ConfigUtil.load_specs(specspath)
        config = ConfigUtil.verify_config(specs, config)

        return config


    def run(self, config):
        pr.print('Prallocating process files and tables.', time=True)
        force = config['run']['force']
        self.create_tables('links', 'nodes', force=force)

        pr.print(f'Loading process metadata and resources.', time=True)
        network_path = config['run']['network_file']
        bin_size = config['run']['bin_size']

        if network_path.split('.')[-1] == 'gz':
            network_file = gzip.open(network_path, mode='rb')
        else:
            network_file = open(network_path, mode='rb')

        parser = iter(iterparse(network_file, events=('start', 'end')))
        evt, root = next(parser)

        links = []
        nodes = []
        count = 0

        for evt, elem in parser:
            if evt == 'start':
                if elem.tag == 'nodes':
                    pr.print('Starting road node parsing.', time=True)
                elif elem.tag == 'links':
                    pr.print(f'Pushing {count % bin_size} nodes to the '
                        'database.', time=True)
                    self.database.write_nodes(nodes)
                    nodes = []
                    root.clear()
                    count = 0
                    pr.print('Starting road link parsing.', time=True)
            elif evt == 'end':
                if elem.tag == 'node':
                    nodes.append((
                        str(elem.get('id')),
                        f'POINT({elem.get("x")} {elem.get("y")})'))
                    count += 1
                    if count % bin_size == 0:
                        pr.print(f'Pushing {bin_size} nodes to '
                            'the database.', time=True)
                        self.database.write_nodes(nodes)
                        nodes = []
                        root.clear()
                        pr.print(f'Continuing nodes parsing.', time=True)
                elif elem.tag == 'link':
                    links.append((
                        str(elem.get('id')),
                        str(elem.get('from')),
                        str(elem.get('to')),
                        float(elem.get('length')),
                        float(elem.get('freespeed')),
                        float(elem.get('capacity')),
                        float(elem.get('permlanes')),
                        int(elem.get('oneway')),
                        str(elem.get('modes'))))
                    count += 1
                    if count % bin_size == 0:
                        pr.print(f'Pushing {bin_size} links to '
                            'the database.', time=True)
                        self.database.write_links(links)
                        links = []
                        root.clear()
                        pr.print(f'Continuing link parsing.', time=True)

        if count % bin_size != 0:
            pr.print(f'Pushing {count % bin_size} links to the database.', time=True)
            self.database.write_links(links)
            links = []
            root.clear()

        network_file.close()

        pr.print('Network road parsing complete.', time=True)

        if config['run']['create_idxs']:
            pr.print(f'Creating indexes for module tables.', time=True)
            self.create_idxs()
            pr.print(f'Index creation complete.', time=True)


    def create_idxs(self):
        for tbl in self.database.tables:
            self.database.create_all_idxs(tbl)


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