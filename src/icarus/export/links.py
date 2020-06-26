
import os
import shapefile
import requests
import logging as log

from argparse import ArgumentParser
from pyproj.transformer import Transformer

from icarus.util.general import counter
from icarus.util.sqlite import SqliteUtil


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


def export_links(database: SqliteUtil, filepath: str, src_epsg: int, 
        prj_epsg: int):

    transformer = Transformer.from_crs(f'epsg:{src_epsg}', 
        f'epsg:{prj_epsg}', always_xy=True, skip_equivalent=True)
    project = transformer.transform

    prjpath = os.path.splitext(filepath)[0] + '.prj'
    with open(prjpath, 'w') as prjfile:
        info = get_wkt_string(prj_epsg)
        prjfile.write(info)

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
            nodes1.point,
            nodes2.point
        FROM links
        INNER JOIN nodes AS nodes1
        ON links.source_node = nodes1.node_id
        INNER JOIN nodes AS nodes2
        ON links.terminal_node = nodes2.node_id;
    '''
    database.cursor.execute(query)
    rows = database.fetch_rows()
    rows = counter(rows, 'Exporting link %s.')

    links = shapefile.Writer(filepath, )
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

    for row in rows:
        props = row[:-2]
        pt1, pt2 = row[-2:]
        x1, y1 = project(*xy(pt1))
        x2, y2 = project(*xy(pt2))

        try:
            links.record(*props)
        except:
            print(props)
            breakpoint()
            exit()
        links.line([((x1, y1), (x2, y2))])

    if links.recNum != links.shpNum:
        log.error('Record/shape misalignment; shapefile exporting failure.')
        raise RuntimeError

    links.close()


def main():
    parser = ArgumentParser()
    main = parser.add_argument_group('main')
    main.add_argument('file', type=str,
        help='file path to save the exported routes to')
    main.add_argument('--epsg', dest='epsg', type=int, default=2223,
        help='epsg system to convert routes to; default is 2223')
        
    common = parser.add_argument_group('common')
    common.add_argument('--folder', type=str, dest='folder', default='.',
        help='file path to the directory containing Icarus run data'
            '; default is the working directory')
    common.add_argument('--log', type=str, dest='log', default=None,
        help='file path to save the process log; by default the log is not saved')
    common.add_argument('--level', type=str, dest='level', default='info',
        help='verbosity level of the process log; default is "info"',
        choices=('notset', 'debug', 'info', 'warning', 'error', 'critical'))
    common.add_argument('--replace', dest='replace', 
        action='store_true', default=False, 
        help='automatically replace existing data; do not prompt the user')
    args = parser.parse_args()

    handlers = []
    handlers.append(log.StreamHandler())
    if args.log is not None:
        handlers.append(log.FileHandler(args.log, 'w'))
    log.basicConfig(
        format='%(asctime)s %(levelname)s %(filename)s:%(lineno)s %(message)s',
        level=getattr(log, args.level.upper()),
        handlers=handlers
    )

    path = lambda x: os.path.abspath(os.path.join(args.folder, x))
    home = path('')


    log.info('Running link export tool.')
    log.info(f'Loading run data from {home}.')

    database = SqliteUtil(path('database.db'), readonly=True)

    try:
        export_links(database, args.file, 2223, args.epsg)
    except:
        log.exception('Critical error while exporting routes:')
        exit(1)

    database.close()


if __name__ == '__main__':
    main()