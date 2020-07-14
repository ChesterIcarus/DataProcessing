
import os
import logging as log
import pandas as pd
import geopandas as gpd
import contextily as ctx
import matplotlib.pyplot as plt

from collections import defaultdict
from argparse import ArgumentParser
from shapely.geometry import LineString

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

    links = []
    for link_id, profile, src_pt, term_pt in rows:
        line = LineString((xy(src_pt), xy(term_pt)))
        x, y = line.coords.xy
        if bounds(x, y):
            link = Link(link_id, line, profile)
            links.append(link)
    
    return links


def load_temperatures(database: SqliteUtil, kind: str, 
            max_idx: int, min_idx: int):
    query = f'''
        SELECT
            mrt_temperatures.temperature_id,
            mrt_temperatures.temperature_idx,
            mrt_temperatures.{kind},
            COUNT(*) AS util
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
    for uuid, idx, temp, util in rows:
        if util > 0:
            temps[uuid][idx - min_idx] = temp

    return temps


def load_extrema(database: SqliteUtil, kind: str):
    query = f'''
        SELECT
            max({kind}),
            min({kind}),
            max(temperature_idx),
            min(temperature_idx)
        FROM mrt_temperatures;
    '''
    database.cursor.execute(query)
    max_temp, min_temp, max_idx, min_idx = next(database.fetch_rows())

    return max_temp, min_temp, max_idx, min_idx


def map_mrt_temperature1(database: SqliteUtil, kind: str):
    os.makedirs('result/mrt_temperatures/', exist_ok=True)

    log.info('Profiling temperature extrema.')
    max_temp, min_temp, max_idx, min_idx = load_extrema(database, kind)

    log.info('Loading network links.')
    links = load_links(database)

    log.info('Loading temperatures.')
    temps = load_temperatures(database, kind, max_idx, min_idx)

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

    for idx in range(min_idx, max_idx + 1):
        fig, ax = plt.subplots(1, figsize=(20, 12))

        log.info(f'Plotting network visual {idx - min_idx}'
            f' of {max_idx - min_idx}.')

        plot = gpdf.plot(column=f'temp_{idx}', cmap='YlOrRd', linewidth=0.5, 
            ax=ax, alpha=1)

        ax.set_title(f'Maricopa {kind.upper()} Temperatures {idx_to_hhmm(idx)}',
            fontdict={'fontsize': '18', 'fontweight' : '3'})

        ctx.add_basemap(plot, source=ctx.providers.Stamen.TonerLite)

        sm = plt.cm.ScalarMappable(cmap='YlOrRd', 
            norm=plt.Normalize(vmin=min_temp, vmax=max_temp))
        sm._A = []
        cbar = fig.colorbar(sm)

        fig.savefig(f'result/mrt_temperatures1/{idx}.png', bbox_inches='tight')

        plt.clf()
        plt.close()


def map_mrt_temperature(database: SqliteUtil, kind: str):
    log.info('Profiling temperature extrema.')
    max_temp, min_temp, max_idx, min_idx = load_extrema(database, kind)

    log.info('Loading network links.')
    links = load_links(database)

    os.makedirs('result/mrt_temperatures1/', exist_ok=True)

    log.info('Loading temperatures.')
    temps = defaultdict(lambda: [None] * (max_idx - min_idx + 1))
    query = f'''
        SELECT
            temperature_id,
            temperature_idx,
            {kind}
        FROM mrt_temperatures;
    '''
    database.cursor.execute(query)
    rows = database.fetch_rows()
    rows = counter(rows, 'Loading temperature profile %s.')

    for uuid, idx, temp in rows:
        temps[uuid][idx - min_idx] = temp
    
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

    for idx in range(min_idx, max_idx + 1):
        fig, ax = plt.subplots(1, figsize=(20, 12))

        log.info(f'Plotting network visual.')
        plot = gpdf.plot(column=f'temp_{idx}', cmap='YlOrRd', linewidth=0.5, 
            ax=ax, alpha=1)

        ax.set_title(f'Maricopa {kind.upper()} Temperatures {idx_to_hhmm(idx)}',
            fontdict={'fontsize': '18', 'fontweight' : '3'})

        ctx.add_basemap(plot, source=ctx.providers.Stamen.TonerLite)

        sm = plt.cm.ScalarMappable(cmap='YlOrRd', 
            norm=plt.Normalize(vmin=min_temp, vmax=max_temp))
        sm._A = []
        cbar = fig.colorbar(sm)

        log.info(f'Saving map.')
        fig.savefig(f'result/mrt_temperatures1/{idx}.png', bbox_inches='tight')

        plt.clf()
        plt.close()


def main():
    parser = ArgumentParser('mrt temperature visualizer')
    
    parser.add_argument('--dir', type=str, dest='dir', default='.',
        help='path to directory containing Icarus run data')
    parser.add_argument('--log', type=str, dest='log', default=None,
        help='path to file to save the process log; not saved by default')
    parser.add_argument('--level', type=str, dest='level', default='info',
        choices=('notset', 'debug', 'info', 'warning', 'error', 'critical'),
        help='verbosity of the process log')

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
    kind = 'mrt'

    map_mrt_temperature(database, kind)


if __name__ == '__main__':
    main()
