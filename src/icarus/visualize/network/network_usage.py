
import logging as log
import networkx as nx
import matplotlib.pyplot as plt
# import geopandas as gpd
# import pandas as pd
# import osmnx as ox
# import requests
# import matplotlib.cm as cm
# import matplotlib.colors as colors
# from shapely.wkt import loads

from icarus.util.sqlite import SqliteUtil


def xy(point: str) -> tuple:
    return tuple(map(float, point[7:-1].split(' ')))


class Network:
    def __init__(self, database: SqliteUtil):
        self.database = database

    
    def fetch_links(self):
        query = '''
            SELECT
                link_id,
                source_node,
                terminal_node
            FROM links; '''
        self.database.cursor.execute(query)
        return self.database.cursor.fetchall()

    
    def fetch_nodes(self):
        query = '''
            SELECT
                node_id,
                point
            FROM nodes; '''
        self.database.cursor.execute(query)
        return self.database.cursor.fetchall()

    
    # def load_links(self) -> gpd.GeoDataFrame:
    #     links = []
    #     for link_id, line in self.fetch_links():
    #         links.append((link_id, loads(line)))
    #     df = pd.DataFrame(links, columns=('id', 'line'))
    #     df['line'] = gpd.GeoSeries(df['line'], crs='EPSG:2223')
    #     df = gpd.GeoDataFrame(df, geometry='line', crs='EPSG:2223')
    #     return df


    # def load_nodes(self) -> gpd.GeoDataFrame:
    #     nodes = []
    #     for node_id, point in self.fetch_nodes():
    #         nodes.append((node_id, loads(point)))
    #     df = pd.DataFrame(nodes, columns=('id', 'point'))
    #     df['point'] = gpd.GeoSeries(df['point'], crs='EPSG:2223')
    #     df = gpd.GeoDataFrame(df, geometry='point', crs='EPSG:2223')
    #     return df


    def plain_map(self):
        log.info('Loading network nodes.')
        nodes = self.fetch_nodes()
        links = self.fetch_links()

        fig = plt.figure(figsize=(12,12))
        ax = plt.subplot(111)
        ax.set_title('Maricopa County', fontsize=14)

        graph = nx.Graph()

        for node_id, point in nodes:
            x, y = xy(point)
            graph.add_node(node_id, pos=(x,y))
        
        for _, source_node, terminal_node in links:
            graph.add_edge(source_node, terminal_node)
        
        pos = nx.get_node_attributes(graph, 'pos')
        nx.draw_networkx(graph, pos=pos, ax=ax)
        
        plt.tight_layout()
        plt.savefig('result/network_usage.png', dpi=600)



if __name__ == '__main__':
    database = SqliteUtil('database.db')
    network = Network(database)
    network.plain_map()
