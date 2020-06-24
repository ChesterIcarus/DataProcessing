
import os
import shapefile
import requests
import logging as log

from shapely.wkt import loads
from shapely.geometry import Point
from argparse import ArgumentParser
from pyproj import Transformer, Geod
from typing import List

from icarus.util.general import counter
from icarus.util.sqlite import SqliteUtil


class Centroid:
    __slots__ = ('id', 'point')

    def __init__(self, uuid: int, point: Point):
        self.id = uuid
        self.point = point


class Node:
    __slots__ = ('id', 'point', 'maz', 'centroid')

    def __init__(self, uuid: int, maz:int, centroid: Centroid, point: Point):
        self.id = uuid
        self.maz = maz
        self.centroid = centroid
        self.point = point


def xy(point: str) -> tuple:
    return tuple(map(float, point[7:-1].split(' ')))


def get_wkt_string(epsg: int) -> str:
    res = requests.request('get', f'https://epsg.io/{epsg}.prettywkt')
    string = res.content.decode().replace(' ', '').replace('\n', '')
    return string


def get_proj_string(epsg: int) -> str:
    res = requests.request('get', f'https://epsg.io/{epsg}.proj4')
    string = res.content.decode().replace('\n', '')
    return string


def load_nodes(database: SqliteUtil, threshold: float, epsg: int = None) -> List[Node]:
    centroids = {}
    nodes = {}

    transformer = Transformer.from_crs('epsg:2223', 
        f'epsg:{epsg}', always_xy=True, skip_equivalent=True)
    transform = transformer.transform

    query = '''
        SELECT
            centroid_id,
            point
        FROM mrt_centroids
        INNER JOIN nodes
        ON mrt_centroids.centroid_id = modes.mrt_centroid;
    '''

    database.cursor.execute(query)
    rows = database.fetch_rows()
    rows = counter(rows, 'Loading centroid %s.')

    log.info('Loading network MRT centroids.')
    for centroid_id, point in rows:
        if centroid_id not in centroids:
            x, y = transform(*xy(point))
            pt = Point(x, y)
            centroids[centroid_id] = Centroid(centroid_id, pt)

    query = '''
        SELECT
            node_id,
            maz,
            mrt_centroid,
            point,
            GROUP_CONCAT(links.link_id, " ")
        FROM nodes;
    '''

        # INNER JOIN links
        # ON links.source_node = nodes.node_id
        # OR links.terminal_node = nodes.node_id
        # GROUP BY links.link_id;

    database.cursor.execute(query)
    rows = database.fetch_rows()
    rows = counter(rows, 'Loading node %s.')

    log.info('Loading network nodes.')
    for node_id, maz, centroid_id, point in rows:
        x, y = transform(*xy(point))
        pt = Point(x, y)
        centroid = centroids[centroid_id]
        nodes[node_id] = Node(node_id, maz, centroid, pt)

    log.info('Filtering nodes by threshold.')
    unmatched = []
    for node in nodes.values():
        centroid = node.centroid
        if node.point.distance(centroid.point) > threshold:
            unmatched.append(node)
    
    return unmatched


def export_map(nodes: List[Node], filepath: str):
    pass


def export_shapefile(nodes: List[Node], filepath: str):
    
    for node in nodes:
        pass
        


def main():
    parser = ArgumentParser('MRT Centroid Analyzer')

    parser.add_argument('threshold', type=float, required=True,
        help='maximum distance of MRT point to network node; units '
            'match those of the chosen coordinate system')
    parser.add_argument('--epsg', type=int, dest='epsg', default=None,
        help='epsg to convert to; defualt is no transformation')
    parser.add_argument('--map', type=str, dest='map', default=None,
        help='location to save map; map not saved by default')
    parser.add_argument('--shapefile', type=str, dest='shapefile', default=None,
        help='location to save shapefile; shapefile not saved by default')

    oper = parser.add_argument_group('operational')
    oper.add_argument('--dir', type=str, dest='dir', default='.',
        help='path to directory containing Icarus run data')
    oper.add_argument('--log', type=str, dest='log', default=None,
        help='path to file to save the process log; not saved by default')
    oper.add_argument('--level', type=str, dest='level', default='info',
        choices=('notset', 'debug', 'info', 'warning', 'error', 'critical'),
        help='verbosity of the process log')

    args = parser.parse_args()

    handlers = [log.StreamHandler()]
    if args.log is not None:
        handlers.append(log.FileHandler(args.log, 'w'))
    log.basicConfig(
        format='%(asctime)s %(levelname)s %(filename)s:%(lineno)s %(message)s',
        level=getattr(log, args.level.upper()),
        handlers=handlers
    )

    path = lambda x: os.path.abspath(os.path.join(args.dir, x))

    database = SqliteUtil(path('.'), readonly=True)

    nodes = load_nodes(database, args.threshold)



if __name__ == '__main__':
    main()
