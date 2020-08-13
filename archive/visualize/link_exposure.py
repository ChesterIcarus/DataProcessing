
import os
import seaborn as sns
import logging as log
import pandas as pd
import geopandas as gpd
import contextily as ctx
import matplotlib.pyplot as plt

from matplotlib.colors import PowerNorm
from math import inf
from collections import defaultdict
from argparse import ArgumentParser
from shapely.geometry import LineString
from pyproj.transformer import Transformer

from icarus.util.sqlite import SqliteUtil
from icarus.util.general import counter


class Link:
    __slots__ = ('id', 'line', 'profile')

    def __init__(self, uuid: str, line: LineString, profile: int):
        self.id = uuid
        self.line = line
        self.profile = profile


def xy(point: str) -> tuple:
    return tuple(map(float, point[7:-1].split(' ')))


def idx_to_hhmm(idx: int):
    hrs = idx // 4
    mins = 15 * (idx % 4) 
    hrs %= 24
    return str(hrs).zfill(2) + ':' + str(mins).zfill(2)


def load_links(database: SqliteUtil):
    query = '''
        SELECT
            links.link_id,
            links.mrt_temperature,
            nodes1.point AS source_point,
            nodes2.point AS terminal_point
        FROM links
        INNER JOIN nodes AS nodes1
        ON links.source_node = nodes1.node_id
        INNER JOIN nodes AS nodes2
        ON links.terminal_node = nodes2.node_id;
    '''
    database.cursor.execute(query)
    rows = database.fetch_rows()
    rows = counter(rows, 'Loading link %s.')

    bounds = lambda x, y: min(x) > 0.5e6 and max(x) < 0.85e6 and \
        min(y) > 0.8e6 and max(y) < 1.0e6

    maxx = -inf
    minx = inf
    maxy = -inf
    miny = inf

    links = []
    for link_id, profile, src_pt, term_pt in rows:
        line = LineString((xy(src_pt), xy(term_pt)))
        x, y = line.coords.xy
        if bounds(x, y):
            link = Link(link_id, line, profile)
            links.append(link)

            maxx = max(maxx, *x)
            minx = min(minx, *x)
            maxy = max(maxy, *y)
            miny = min(miny, *y)

    extrema = ((minx, miny), (maxx, maxy))
    
    return links, extrema


def load_extrema(database: SqliteUtil):
    query = f'''
        SELECT
            max(temperature_idx),
            min(temperature_idx)
        FROM mrt_temperatures;
    '''
    database.cursor.execute(query)
    max_idx, min_idx = next(database.fetch_rows())

    return max_idx, min_idx


def load_temperatures(database: SqliteUtil, kind: str, metric: str, 
            max_idx: int, min_idx: int):
    metrics = {
        'exposure': f'SUM(output_events.exposure) / link.length AS util',
        'temperature': f'mrt_temperatures.{kind} AS util',
        'utilization': 'COUNT(*) AS util'
    }
    select = metrics[metric]
    
    query = f'''
        SELECT
            mrt_temperatures.temperature_id,
            mrt_temperatures.temperature_idx,
            {select}            
        FROM mrt_temperatures
        INNER JOIN links
        ON links.mrt_temperature = mrt_temperatures.temperature_id
        INNER JOIN output_events
        ON output_events.link_id = links.link_id
        WHERE output_events.start >= mrt_temperatures.temperature_idx * 900
        AND output_events.end < mrt_temperatures.temperature_idx * 900 + 900
        GROUP BY temperature_id, temperature_idx;
    '''
    database.cursor.execute(query)
    rows = database.fetch_rows()
    rows = counter(rows, 'Loading temperature profile %s.')

    temps = defaultdict(lambda: [None] * (max_idx - min_idx + 1))
    for uuid, idx, util in rows:
        if util > 0:
            temps[uuid][idx - min_idx] = util

    return temps


def map_mrt_temperature(database: SqliteUtil, kind: str, metric: str):
    os.makedirs('result/mrt_temperatures/', exist_ok=True)

    log.info('Profiling temperature extrema.')
    max_idx, min_idx = load_extrema(database)

    log.info('Loading network links.')
    links, bounds = load_links(database)

    log.info('Loading temperatures.')
    temps = load_temperatures(database, kind, metric, max_idx, min_idx)

    def generate():
        for link in links:
            temp = temps[link.profile]
            yield (link.id, *temp, link.line)

    log.info('Forming dataframes.')
    cols = [f'temp_{idx}' for idx in range(min_idx, max_idx + 1)]
    df = pd.DataFrame(generate(), columns=('id', *cols, 'line'))
    df['line'] = gpd.GeoSeries(df['line'], crs='EPSG:2223')
    gpdf = gpd.GeoDataFrame(df, geometry='line', crs='EPSG:2223')
    gpdf = gpdf.to_crs(epsg=3857)

    del links, temps, df

    max_util = max(gpdf[cols].max())
    min_util = min(gpdf[cols].min())

    transformer = Transformer.from_crs(f'epsg:2223', 
        f'epsg:3857', always_xy=True, skip_equivalent=True)
    
    project = lambda pt: transformer.transform(*pt)
    bounds = tuple(map(project, bounds))

    for idx in range(min_idx, max_idx + 1):
        fig, ax = plt.subplots(1, figsize=(20, 12))

        log.info(f'Plotting network visual {idx - min_idx}'
            f' of {max_idx - min_idx}.')

        plot = gpdf.plot(column=f'temp_{idx}', cmap='YlOrRd', linewidth=0.5, 
            ax=ax, alpha=1)

        ax.set_xbound(bounds[0][0], bounds[1][0])
        ax.set_ybound(bounds[0][1], bounds[1][1])
        
        ax.set_title(f'Maricopa {kind.upper()} Temperatures {idx_to_hhmm(idx)}',
            fontdict={'fontsize': '18', 'fontweight' : '3'})

        ctx.add_basemap(plot, source=ctx.providers.Stamen.TonerLite)

        sm = plt.cm.ScalarMappable(cmap='YlOrRd', 
            norm=plt.Normalize(vmin=min_util, vmax=max_util))
        sm._A = []
        fig.colorbar(sm)

        fig.savefig(f'result/mrt_temperatures/{idx}.png', bbox_inches='tight')

        plt.clf()
        plt.close()


def test(database: SqliteUtil):
    log.info('Fetching network link data.')
    query = '''
        SELECT
            links.link_id,
            nodes1.point AS source_point,
            nodes2.point AS terminal_point,
            links.exposure
        FROM links
        INNER JOIN nodes AS nodes1
        ON links.source_node = nodes1.node_id
        INNER JOIN nodes AS nodes2
        ON links.terminal_node = nodes2.node_id
        WHERE links.exposure > 0.0;
    '''
    database.cursor.execute(query)
    result = database.fetch_rows()

    log.info('Filtering and packing data into dataframes.')

    region = lambda x, y: min(x) > 0.5e6 and max(x) < 0.85e6 and \
        min(y) > 0.8e6 and max(y) < 1.0e6

    global maxx, minx, maxy, miny

    maxx = -inf
    minx = inf
    maxy = -inf
    miny = inf

    def links():
        global maxx, minx, maxy, miny
        for uuid, source, dest, exp in result:
            link = LineString((xy(source), xy(dest)))
            x, y = link.coords.xy
            if region(x, y) and exp >= 2.5e5:
                maxx = max(maxx, *x)
                minx = min(minx, *x)
                maxy = max(maxy, *y)
                miny = min(miny, *y)

                yield (uuid, exp, link)

    df = pd.DataFrame(links(), columns=('id', 'exposure', 'line'))
    df['line'] = gpd.GeoSeries(df['line'], crs='epsg:2223')
    gpdf = gpd.GeoDataFrame(df, geometry='line', crs='EPSG:2223')
    gpdf = gpdf.to_crs(epsg=3857)

    del df, result

    max_exp = gpdf['exposure'].max()
    min_exp = gpdf['exposure'].min()
    bounds = ((minx, miny), (maxx, maxy))

    axes = sns.distplot(gpdf['exposure'])
    plot = axes.get_figure()
    plot.savefig('result/link_exposure_dist.png', bbox_inches='tight')
    plot.clf()
    
    transformer = Transformer.from_crs(f'epsg:2223', 
        f'epsg:3857', always_xy=True, skip_equivalent=True)
    
    project = lambda pt: transformer.transform(*pt)
    bounds = tuple(map(project, bounds))

    log.info('Graphing network links.')

    fig, ax = plt.subplots(1, figsize=(20, 12))
    plot = gpdf.plot(column=f'exposure', cmap='YlOrRd', 
        linewidth=0.5, ax=ax, alpha=1)

    ax.set_xbound(bounds[0][0], bounds[1][0])
    ax.set_ybound(bounds[0][1], bounds[1][1])
    
    ax.set_title(f'Maricopa Cummulative Exposure per Foot',
        fontdict={'fontsize': '18', 'fontweight' : '3'})

    ctx.add_basemap(plot, source=ctx.providers.Stamen.TonerLite)

    
    sm = plt.cm.ScalarMappable(cmap='YlOrRd', 
        norm=PowerNorm(0.1, vmin=min_exp, vmax=max_exp))
    sm._A = []
    fig.colorbar(sm)

    log.info('Saving map.')

    fig.savefig(f'result/link_exposure.png', bbox_inches='tight')

    plt.clf()
    plt.close()
    

def main():
    parser = ArgumentParser('link exposure visualizer')
    
    parser.add_argument('--dir', type=str, dest='dir', default='.',
        help='path to directory containing Icarus run data')
    parser.add_argument('--log', type=str, dest='log', default=None,
        help='path to file to save the process log; not saved by default')
    parser.add_argument('--level', type=str, dest='level', default='info',
        choices=('notset', 'debug', 'info', 'warning', 'error', 'critical'),
        help='verbosity of the process log')

    parser.add_argument('--metric', type=str, dest='metric', default='exposure',
        choices=('exposure', 'temperature', 'utilization'),
        help='the metric used to weight the graph')
    parser.add_argument('--temperature', type=str, dest='temperature', default='mrt',
        choices=('mrt', 'pet', 'utci', 'air'),
        help='the kind of temperature profile to use in calcualting metric')    

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

    database = SqliteUtil('database.db', readonly=True)

    # map_mrt_temperature(database, args.temperature, args.metric)
    test(database)


if __name__ == '__main__':
    main()
