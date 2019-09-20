
from xml.etree.ElementTree import iterparse

from icarus.network.road_parser.road_parser_db import RoadParserDatabaseHandle
from icarus.util.print import Printer as pr

class RoadParser:
    def __init__(self, database, encoding):
        self.database = RoadParserDatabaseHandle(database)
        self.encoding = encoding

    def parse_road(self, filepath, bin_size=1000000):
        pr.print(f'Beginning network road parsing from {filepath}.', time=True)

        parser = iterparse(filepath, events=('start', 'end'))
        parser = iter(parser)
        evt, root = next(parser)

        links = []
        nodes = []
        bin_count = 0

        for evt, elem in parser:
            if evt == 'start':
                if elem.tag == 'nodes':
                    pr.print('Starting road node parsing.', time=True)
                elif elem.tag == 'links':
                    pr.print('Starting road link parsing.', time=True)
            elif evt == 'end':
                if elem.tag == 'node':
                    nodes.append((
                        int(elem.get('id')),
                        f'POINT({elem.get("x")} {elem.get("y")})'))
                    bin_count += 1
                elif elem.tag == 'link':
                    links.append((
                        int(elem.get('id')),
                        int(elem.get('from')),
                        int(elem.get('to')),
                        float(elem.get('length')),
                        float(elem.get('freespeed')),
                        float(elem.get('capacity')),
                        float(elem.get('permlanes')),
                        bool(int(elem.get('oneway'))),
                        str(elem.get('modes'))))
                    bin_count += 1
                elif elem.tag == 'nodes':
                    pr.print(f'Pushing {len(nodes)} nodes to the database.', time=True)
                    self.database.write_nodes(nodes)
                    nodes = []
                    bin_count = 0
                    root.clear()
                elif elem.tag == 'links':
                    pr.print(f'Pushing {len(links)} links to the database.', time=True)
                    self.database.write_nodes(links)
                    links = []
                    bin_count = 0
                    root.clear()
                if bin_count == bin_size:
                    if len(nodes):
                        pr.print(f'Pushing {bin_count} nodes to the database.', time=True)
                        self.database.write_nodes(links)
                        links = []
                    elif len(links):
                        pr.print(f'Pushing {bin_count} links to the database.', time=True)
                        self.database.write_nodes(links)
                        links = []
                    bin_count = 0
                    root.clear()

        pr.print('Network road parsing complete.', time=True)

