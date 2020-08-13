
import os
import pandas as pd
import logging as log
import geopandas as gpd
import contextily as ctx
import matplotlib.pyplot as plt

from mpl_toolkits.axes_grid1 import make_axes_locatable
from shapely.wkt import loads
from typing import Callable, List
from argparse import ArgumentParser, SUPPRESS

from icarus.util.sqlite import SqliteUtil


def sorted_lte_portion(array, value):
    high = len(array)
    low = 0
    portion: float
    if array[0] > value:
        portion = 0.0
    elif array[-1] < value:
        portion = 1.0
    else:
        while low < high:
            idx = (high + low) // 2
            point = array[idx]
            if point > value or low == idx:
                high = idx
            else:
                low = idx
        portion = (low + 1) / len(array)
    return portion


def plot_trips_map_all(database: SqliteUtil, path: Callable[[str], str], 
        bounds: List[float]):
    log.info('Fetching network region data.')
    query = '''
        SELECT
            maz,
            region
        FROM regions;
    '''
    database.cursor.execute(query)
    result = database.fetch_rows()

    def load_regions():
        for maz, region in result:
            yield maz, loads(region)

    log.info('Building region dataframe.')
    cols = ('maz', 'region')
    regions = pd.DataFrame(load_regions(), columns=cols)
    regions = regions.set_index('maz')

    log.info('Fetching trips data by region and purpose.')
    query = '''
        SELECT
            maz,
            COUNT(*) FILTER(WHERE purp = 0),
            COUNT(*) FILTER(WHERE purp = 1),
            COUNT(*) FILTER(WHERE purp = 2),
            COUNT(*) FILTER(WHERE purp = 3),
            COUNT(*) FILTER(WHERE purp IN (4, 41, 411, 42)),
            COUNT(*) FILTER(WHERE purp = 5),
            COUNT(*) FILTER(WHERE purp = 6),
            COUNT(*) FILTER(WHERE purp IN (7, 71, 72, 73)),
            COUNT(*) FILTER(WHERE purp = 8),
            COUNT(*) FILTER(WHERE purp = 9),
            COUNT(*) FILTER(WHERE purp = 10),
            COUNT(*) FILTER(WHERE purp = 11),
            COUNT(*) FILTER(WHERE purp = 12),
            COUNT(*) FILTER(WHERE purp = 13),
            COUNT(*) FILTER(WHERE purp = 14),
            COUNT(*) FILTER(WHERE purp = 15),
            COUNT(*) FILTER(WHERE purp = 16)
        FROM (
            SELECT
                destMaz AS maz,
                destPurp AS purp
            FROM trips
            UNION ALL
            SELECT
                origMaz AS maz,
                origPurp AS purp
            FROM trips
            WHERE personTripNum = 1
        )
        GROUP BY maz;
    '''
    database.cursor.execute(query)
    result = database.fetch_rows()
    
    def load_result():
        for maz, *acts in result:
            yield (maz, *acts, sum(acts))

    log.info('Building trip dataframe.')
    cols = (
        'maz',
        'home',
        'workplace',
        'university',
        'school',
        'escort',
        'shopping',
        'other maintenance',
        'eating out',
        'visiting',
        'other discretionary',
        'special event',
        'work',
        'work business',
        'work lunch',
        'work other',
        'work related',
        'asu',
        'all'
    )
    trips = pd.DataFrame(load_result(), columns=cols)
    trips = trips.set_index('maz')

    log.info('Joining regions and trips.')
    trips = regions.join(trips, on='maz')
    trips = trips.replace(0, None)
    trips['region'] = gpd.GeoSeries(trips['region'], crs='epsg:2223')
    trips = gpd.GeoDataFrame(trips, geometry='region', crs='epsg:2223')

    del regions, result

    for col in cols[1:]:
        log.info('Plotting map of regions with activity %s.' % col)
        fig, ax = plt.subplots(1, 1, figsize=(12,10))
        divider = make_axes_locatable(ax)
        cax = divider.append_axes('right', size='5%', pad=0.1)
        plot = trips.plot(column=col, cmap='YlOrRd', linewidth=1, 
                ax=ax, cax=cax, legend=True, alpha=0.75)
        ax.set_title(f'occurence of {col} activites in mazs')
        if bounds is not None:
            ax.set_xlim(bounds[0], bounds[2])
            ax.set_ylim(bounds[1], bounds[3])
        ctx.add_basemap(plot, source=ctx.providers.Stamen.TonerLite, 
                attribution='', crs='epsg:2223')
        vmin = trips[col].min()
        vmax = trips[col].max()
        sm = plt.cm.ScalarMappable(cmap='YlOrRd', 
            norm=plt.Normalize(vmin=vmin, vmax=vmax))
        sm._A = []
        fig.tight_layout()
        name = col.replace(' ', '_')
        savepath = path('visuals/regions/trips_%s.png' % name)
        fig.savefig(savepath, dpi=600, bbox_inches='tight')
        plt.clf()


def plot_parcels_map_all(database: SqliteUtil, path: Callable[[str], str], 
        bounds: List[float]):
    log.info('Fetching network region data.')
    query = '''
        SELECT
            maz,
            region
        FROM regions;
    '''
    database.cursor.execute(query)
    rows = database.fetch_rows()

    def load_regions():
        for maz, region in rows:
            yield maz, loads(region)

    log.info('Building region dataframe.')
    cols = ('maz', 'region')
    regions = pd.DataFrame(load_regions(), columns=cols)
    regions = regions.set_index('maz')

    query = '''
        SELECT
            maz,
            COUNT(*) FILTER(WHERE type = "residential") AS res,
            COUNT(*) FILTER(WHERE type = "commercial") AS com,
            COUNT(*) FILTER(WHERE type = "other") AS oth
        FROM parcels
        GROUP BY maz;
    '''
    database.cursor.execute(query)
    rows = database.fetch_rows()

    def load_parcels():
        for maz, *count in rows:
            yield (maz, *count, sum(count))
    
    cols = ('maz', 'residential', 'commercial', 'other', 'all')
    parcels = pd.DataFrame(load_parcels(), columns=cols)
    parcels = parcels.set_index('maz')

    parcels = regions.join(parcels, on='maz')
    parcels = parcels.replace(0, None)
    parcels['region'] = gpd.GeoSeries(parcels['region'], crs='epsg:2223')
    parcels = gpd.GeoDataFrame(parcels, geometry='region', crs='epsg:2223')

    del regions, rows

    for col in cols[1:]:
        log.info('Plotting map of %s parcels.' % col)
        fig, ax = plt.subplots(1, 1, figsize=(12,10))
        divider = make_axes_locatable(ax)
        cax = divider.append_axes('right', size='5%', pad=0.1)
        plot = parcels.plot(column=col, cmap='YlOrRd', linewidth=1, 
                ax=ax, cax=cax, legend=True, alpha=0.75)
        ax.set_title(f'occurence of {col} parcels in mazs')
        if bounds is not None:
            ax.set_xlim(bounds[0], bounds[2])
            ax.set_ylim(bounds[1], bounds[3])
        ctx.add_basemap(plot, source=ctx.providers.Stamen.TonerLite, 
                attribution='', crs='epsg:2223')
        vmin = parcels[col].min()
        vmax = parcels[col].max()
        sm = plt.cm.ScalarMappable(cmap='YlOrRd', 
            norm=plt.Normalize(vmin=vmin, vmax=vmax))
        sm._A = []
        fig.tight_layout()
        name = col.replace(' ', '_')
        savepath = path('visuals/regions/parcels_%s.png' % name)
        fig.savefig(savepath, dpi=600, bbox_inches='tight')
        plt.clf()


def plot_trips_per_parcel(database: SqliteUtil, path: Callable[[str], str], 
        bounds: List[float]):
    log.info('Fetching network region data.')
    query = '''
        SELECT
            maz,
            region,
            pcount,
            tcount
        FROM regions
        LEFT JOIN (
            SELECT
                maz,
                COUNT(*) AS pcount
            FROM parcels
            WHERE type IN ("residential", "commercial", "other")
            GROUP BY maz
        ) 
        USING(maz)
        LEFT JOIN (
            SELECT
                maz,
                COUNT(*) AS tcount
            FROM (
                SELECT destMaz AS maz
                FROM trips
                UNION ALL
                SELECT origMaz AS maz
                FROM trips
                WHERE personTripNum = 1
            )
            GROUP BY maz
        )
        USING(maz);
    '''
    database.cursor.execute(query)
    rows = database.fetch_rows()

    def load_regions():
        for maz, region, parcels, trips in rows:
            geometry = loads(region)
            ratio = None
            if trips is not None and parcels is not None:
                ratio  = trips / parcels if parcels > 0 else None
            yield (maz, geometry, parcels, trips, ratio)

    cols = ('maz', 'region', 'parcels', 'trips', 'ratio')
    regions = pd.DataFrame(load_regions(), columns=cols)
    regions['region'] = gpd.GeoSeries(regions['region'], crs='epsg:2223')
    regions = gpd.GeoDataFrame(regions, geometry='region', crs='epsg:2223')

    log.info('Plotting map of trips to parcels.')
    fig, ax = plt.subplots(1, 1, figsize=(12,10))
    divider = make_axes_locatable(ax)
    cax = divider.append_axes('right', size='5%', pad=0.1)
    plot = regions.plot(column='ratio', cmap='YlOrRd', linewidth=1, 
            ax=ax, cax=cax, legend=True, alpha=0.75)
    ax.set_title(f'ratio of trips to parcels per maz')
    if bounds is not None:
        ax.set_xlim(bounds[0], bounds[2])
        ax.set_ylim(bounds[1], bounds[3])
    ctx.add_basemap(plot, source=ctx.providers.Stamen.TonerLite, 
            attribution='', crs='epsg:2223')
    vmin = regions['ratio'].min()
    vmax = regions['ratio'].max()
    sm = plt.cm.ScalarMappable(cmap='YlOrRd', 
        norm=plt.Normalize(vmin=vmin, vmax=vmax))
    sm._A = []
    fig.tight_layout()
    savepath = path('visuals/regions/trips_per_parcel.png')
    fig.savefig(savepath, dpi=600, bbox_inches='tight')
    plt.clf()


def main():
    desc = (
        ''
    )
    parser = ArgumentParser('icarus.visualize.input.regions',
            description=desc, add_help=False)

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
    os.makedirs(path('visuals/regions/'), exist_ok=True)

    logpath = path('logs/visualize_input_regions.log')
    dbpath = path('database.db')

    handlers = []
    handlers.append(log.StreamHandler())
    handlers.append(log.FileHandler(logpath))
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

    database = SqliteUtil(dbpath, readonly=True)

    bounds = [ 538469.71851555, 820213.86426396, 795753.75497050, 978336.65984825 ]
    # plot_parcels_map_all(database, path, bounds)
    # plot_trips_map_all(database, path, bounds)
    plot_trips_per_parcel(database, path, bounds)


if __name__ == '__main__':
    main()