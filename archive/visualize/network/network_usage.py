
import logging as log
import networkx as nx
import matplotlib.pyplot as plt

from icarus.util.sqlite import SqliteUtil


def xy(point: str) -> tuple:
    return tuple(map(float, point[7:-1].split(' ')))

    
def fetch_links(database:SqliteUtil):
    query = '''
        SELECT
            link_id,
            source_node,
            terminal_node
        FROM links; '''
    database.cursor.execute(query)
    return database.cursor.fetchall()


def fetch_nodes(database: SqliteUtil):
    query = '''
        SELECT
            node_id,
            point
        FROM nodes; '''
    database.cursor.execute(query)
    return database.cursor.fetchall()


def map_network_usage(database: SqliteUtil):
    print('Loading network nodes and links.')
    nodes = fetch_nodes(database)
    links = fetch_links(database)

    fig = plt.figure(figsize=(12,12))
    ax = plt.subplot(111)
    ax.set_title('Maricopa County', fontsize=14)

    graph = nx.Graph()

    print('Adding nodes to the graph.')

    for node_id, point in nodes:
        x, y = xy(point)
        graph.add_node(node_id, pos=(x,y))

    print('Adding links to the graph.')
    
    for _, source_node, terminal_node in links:
        graph.add_edge(source_node, terminal_node)
    
    print('Drawing the graph.')

    pos = nx.get_node_attributes(graph, 'pos')
    nx.draw_networkx(graph, pos=pos, ax=ax, with_labels=False, node_size=0)
    
    print('Saving the graph.')

    plt.tight_layout()
    plt.savefig('result/network_usage.png', dpi=600)



if __name__ == '__main__':
    database = SqliteUtil('database.db')
    map_network_usage(database)
