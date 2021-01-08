
import os
import rtree
import requests
import shapefile
import logging as log

from typing import Callable, Tuple
from shapely.geometry import Polygon, Point, shape
from pyproj.transformer import Transformer
from argparse import ArgumentParser, SUPPRESS
from multiprocessing import Pool, Queue, Process, Manager

from icarus.util.general import counter
from icarus.util.general import bins
from icarus.util.apsw import Database


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

def write_shapefile_queue(queue: Queue, filepath: str, filtered: bool):
    log.debug(f'Opening {filepath} for writing.')

    links = shapefile.Writer(filepath)
    links.field('link_id', 'C')
    links.field('source_node', 'C')
    links.field('terminal_node', 'C')
    links.field('length', 'N')
    links.field('freespeed', 'N')
    links.field('capacity', 'N')
    links.field('permlanes', 'N')
    links.field('oneway', 'N')
    links.field('modes', 'C')
    links.field('air_temperature', 'N')
    links.field('mrt_temperature', 'N')
    links.field('utilization', 'N')
    links.field('air_exposure', 'N')
    links.field('mrt_exposure', 'N')

    count = 0
    request = queue.get()
    while request != 'exit':
        count += len(request)
        for props, line in request:
            links.record(*props)
            links.line(line)
        log.debug(f'Writing link {count} to shapefile.')
        request = queue.get()
    
    if links.recNum != links.shpNum:
        log.error('Record/shape misalignment; shapefile exporting failure.')
        raise RuntimeError

    if filtered:
        log.debug(f'Network has {links.recNum} links after geospatial filtering.')

    links.close()

def filter_links_thread(queue: Queue, links: Tuple, boundary: Polygon, epsg: int):
    valid: Callable[[Point,Point],bool]
    if boundary is not None:
        b = boundary.bounds
        valid = lambda pt1, pt2: all((
            pt1.x >= b[0], pt2.x >= b[0], 
            pt1.y >= b[2], pt2.y >= b[2],
            pt1.x <= b[1], pt2.x <= b[1], 
            pt1.y <= b[3], pt2.y <= b[3]
        )) and boundary.contains(pt1) and boundary.contains(pt2)
    else:
        valid = lambda pt1, pt2: True
    
    transformer = Transformer.from_crs('epsg:2223', f'epsg:{epsg}', True, True)
    project = transformer.transform

    result = []
    for cols in links:
        props = cols[:-2]
        pt1, pt2 = cols[-2:]
        pt1 = Point(xy(pt1))
        pt2 = Point(xy(pt2))
        if valid(pt1, pt2):
            x1, y1 = project(pt1.x, pt1.y)
            x2, y2 = project(pt2.x, pt2.y)
            line = [((x1, y1), (x2, y2))]
            result.append((props, line))

    queue.put(result)

def load_boundary(shppath: str) -> Polygon:
    prjpath = os.path.splitext(shppath)[0] + '.prj'
    with open(prjpath, 'r') as prjfile:
        prjstr = prjfile.read()
    
    transformer = Transformer.from_crs(prjstr, 'epsg:2223', True, True)
    project = transformer.transform

    reader = shapefile.Reader(shppath)
    record = next(iter(reader))
    record.shape.points = [project(*pt) for pt in record.shape.points]
    polygon = Polygon(shape(record.shape))
    reader.close()

    return polygon

def export_links(database: Database, filepath: str, bounds: str = None,
                 epsg: int = 2223, merge: bool = False):
    boundary: Polygon = None
    if bounds is not None:
        boundary = load_boundary(bounds)

    log.info('Fetching and merging all event and link data.')

    query = '''
        SELECT
            links.link_id,
            links.source_node,
            links.terminal_node,
            links.length,
            links.freespeed,
            links.capacity,
            links.permlanes,
            links.oneway,
            links.modes,
            links.air_temperature,
            links.mrt_temperature,
            COUNT(events.event_id) AS utilization,
            SUM(events.air_exposure) AS air_exposure,
            SUM(events.mrt_exposure) AS mrt_exposure,
            nodes1.point,
            nodes2.point
        FROM links
        LEFT JOIN events
        USING(link_id)
        LEFT JOIN nodes AS nodes1
        ON links.source_node = nodes1.node_id
        LEFT JOIN nodes AS nodes2
        ON links.terminal_node = nodes2.node_id
        GROUP BY link_id;
    '''

    # query = '''
    #     SELECT
    #         links.link_id,
    #         links.source_node,
    #         links.terminal_node,
    #         links.length,
    #         links.freespeed,
    #         links.capacity,
    #         links.permlanes,
    #         links.oneway,
    #         links.modes,
    #         nodes1.point,
    #         nodes2.point
    #     FROM links
    #     LEFT JOIN nodes AS nodes1
    #     ON links.source_node = nodes1.node_id
    #     LEFT JOIN nodes AS nodes2
    #     ON links.terminal_node = nodes2.node_id
    #     GROUP BY link_id;
    # '''

    database.cursor.execute(query)
    rows = database.cursor.fetchall()

    count = len(rows)
    log.debug(f'Network has {count} total links.')

    if merge:
        log.info('Merging coincidental directional links.')
        merged = {}
        for row in rows:
            n1, n2 = row[-2], row[-1]
            n = frozenset((n1, n2))
            if n in merged:
                uuid = row[0]
                merged[n][0] += f',{uuid}'
                merged[n][7] = 0
            else:
                merged[n] = list(row)
        rows = tuple(merged.values())
        count = len(rows)
        log.debug(f'Network has {count} after merging.')
        del merged

    log.info('Filtering and writing links to shapefile.')

    manager = Manager()
    pool = Pool()
    queue = manager.Queue(4)
    filtered = boundary is not None
    jobs = ((queue, job, boundary, epsg) for job in bins(rows, 10000))

    pool.apply_async(write_shapefile_queue, (queue, filepath, filtered))
    pool.starmap(filter_links_thread, jobs)
    queue.put('exit')
    pool.close()
    pool.join()

    prjpath = os.path.splitext(filepath)[0] + '.prj'
    with open(prjpath, 'w') as prjfile:
        prj = get_wkt_string(2223)
        prjfile.write(prj)


def main():
    desc = (
        ''
    )
    parser = ArgumentParser('icarus.export.links', description=desc, add_help=False)
    main = parser.add_argument_group('main options')
    main.add_argument('file', type=str, help='file path to save the exported links to')
    main.add_argument('--boundary', type=str, dest='bounds', default=None,
        help='file path to shapefile which defines export boundary')
    main.add_argument('--epsg', dest='epsg', type=int, default=2223,
        help='epsg system to convert links to; default is 2223')
    main.add_argument('--merge', dest='merge', action='store_true', default=False,
        help='merge links with the same set of source and temrinal nodes; '
             'sets directional to 0 and link_id to a comma delimited list')
        
    general = parser.add_argument_group('general options')
    general.add_argument('--help', action='help', default=SUPPRESS,
        help='show this help menu and exit process')
    general.add_argument('--dir', type=str, dest='dir', default='.',
        help='path to simulation data; default is current working directory')
    general.add_argument('--log', type=str, dest='log', default=None,
        help='location to save additional logfiles')
    general.add_argument('--level', type=str, dest='level', default='info',
        choices=('notset', 'debug', 'info', 'warning', 'error', 'critical'),
        help='level of verbosity to print log messages')
    general.add_argument('--force', action='store_true', dest='force', 
        default=False, help='skip prompts for deleting files/tables')
    
    args = parser.parse_args()

    path = lambda x: os.path.abspath(os.path.join(args.dir, x))
    os.makedirs(path('logs'), exist_ok=True)
    homepath = path('')
    logpath = path('logs/export_links.log')
    dbpath = path('database.db')

    handlers = []
    handlers.append(log.StreamHandler())
    handlers.append(log.FileHandler(logpath, 'w'))
    if args.log is not None:
        handlers.append(log.FileHandler(args.log, 'w'))
    if args.level == 'debug':
        frmt = '%(asctime)s %(levelname)s %(filename)s:%(lineno)s %(message)s'
    else:
        frmt = '%(asctime)s %(levelname)s %(message)s'
    log.basicConfig(
        format=frmt,
        level=getattr(log, args.level.upper()),
        handlers=handlers
    )

    log.info('Running link exporting module.')
    log.info(f'Loading data from {homepath}.')
    log.info('Verifying process metadata/conditions.')    

    database = Database(dbpath, readonly=True)

    export_links(database, args.file, args.bounds, args.epsg, args.merge)


if __name__ == '__main__':
    main()
