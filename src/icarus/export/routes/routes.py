
import shapefile
import logging as log

from typing import List
from pyproj import Transformer

from icarus.util.sqlite import SqliteUtil
from icarus.util.general import counter


class Node:
    __slots__ = ('x', 'y')

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y



class Link:
    __slots__ = ('source_node', 'terminal_node', 'length')

    def __init__(self, source_node: Node, terminal_node: Node, length: float):
        self.source_node = source_node
        self.terminal_node = terminal_node
        self.length = length



def export_routes(database: SqliteUtil, modes: List[str], 
        filepath: str, skip_empty: bool, epsg: int):

    transform = lambda x, y: (x, y)
    if epsg is not None and epsg != 2223:
        transformer = Transformer.from_crs('epsg:2223', 
            f'epsg:{epsg}', always_xy=True)
        transform = transformer.transform

    log.info('Loading network node data.')
    query = '''
        SELECT
            node_id,
            point
        FROM nodes;
    '''
    nodes = {}
    database.cursor.execute(query)
    result = counter(database.fetch_rows(), 'Loading node %s.')

    for node_id, point in result:
        x, y = transform(*map(float, point[7:-1].split(' ')))
        nodes[node_id] = Node(x, y)
    
    log.info('Loading network link data.')
    query = '''
        SELECT 
            link_id,
            source_node,
            terminal_node,
            length
        FROM links;
    '''
    links = {}
    database.cursor.execute(query)
    result = counter(database.fetch_rows(), 'Loading link %s.')

    for link_id, source_node, terminal_node, length in result:
        links[link_id] = Link(
            nodes[source_node], 
            nodes[terminal_node], 
            length
        )


    log.info('Loading network routing data.')
    query = f'''
        SELECT
            output_legs.leg_id,
            output_legs.agent_id,
            output_legs.agent_idx,
            output_legs.mode,
            output_legs.duration,
            GROUP_CONCAT(output_events.link_id, " ")
        FROM output_legs
        LEFT JOIN output_events
        ON output_legs.leg_id = output_events.leg_id
        WHERE output_legs.mode IN {tuple(modes)}
        GROUP BY
            output_legs.leg_id
        ORDER BY
            output_events.leg_id,
            output_events.leg_idx;
    '''
    database.cursor.execute(query)
    result = counter(database.fetch_rows(block=1000000),
        'Exporting route %s.')

    routes = shapefile.Writer(filepath)
    routes.field('leg_id', 'N')
    routes.field('agent_id', 'N')
    routes.field('agent_idx', 'N')
    routes.field('mode', 'C')
    routes.field('duration', 'N')
    routes.field('length', 'N')

    

    log.info('Exporting simulation routes to shapefile.')
    for leg_id, agent_id, agent_idx, mode, duration, events in result:
        if events is not None:
            route = [links[l] for l in events.split(' ')]
            line = [(link.source_node.x, link.source_node.y) for link in route]
            line.append((route[-1].terminal_node.x, route[-1].terminal_node.y))
            length = sum((link.length for link in route))
            routes.record(leg_id, agent_id, agent_idx, mode, duration, length)
            routes.line([line])
        elif not skip_empty:
            routes.record(leg_id, agent_id, agent_idx, mode, duration, None)
            routes.null()

    if routes.recNum != routes.shpNum:
        log.error('Record/shape misalignment; internal exporting failure.')

    routes.close()

    log.info(f'Routing export complete: wrote {routes.shpNum} routes.')
