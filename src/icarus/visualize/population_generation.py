
import os
import pandas as pd
import seaborn as sns
import logging as log
import geopandas as gpd
import contextily as ctx
import matplotlib.pyplot as plt

from typing import List
from shapely.wkt import loads
from collections import defaultdict
from argparse import ArgumentParser
from pyproj.transformer import Transformer
from mpl_toolkits.axes_grid1 import ImageGrid

from icarus.util.sqlite import SqliteUtil


def fetch_regions(database: SqliteUtil):
    query = '''
        SELECT
            maz,
            region
        FROM regions;
    '''
    database.cursor.execute(query)
    result = database.fetch_rows()

    regions = []
    for maz, region in result:
        polygon = loads(region)
        regions.append((maz, polygon))

    return regions


def fetch_trips(database: SqliteUtil):
    query= '''
        SELECT
            trips.origMaz,
            trips.destMaz,
            trips.mode,
            agents.agent_id IS NOT NULL AS kept
        FROM trips
        LEFT JOIN agents
        ON trips.hhid = agents.household_id
        AND trips.pnum = agents.household_idx
        LEFT JOIN legs
        ON legs.agent_id = agents.agent_id
        AND trips.personTripNum = legs.agent_idx + 1;
    '''
    database.cursor.execute(query)
    result = database.fetch_rows()

    rmv_trips = defaultdict(lambda: [0, 0, 0, 0])
    all_trips = defaultdict(lambda: [0, 0, 0, 0])

    modes = {
        1: 0,   8: 1,
        2: 0,   9: 1,
        3: 0,   10: 1,
        4: 0,   11: 2,
        5: 1,   12: 3,
        6: 1,   13: 0,
        7: 1,   14: 0   
    }
    
    for origMaz, destMaz, mode, kept in result:
        mode = modes[mode]
        all_trips[origMaz][mode] += 1
        all_trips[destMaz][mode] += 1
        if not kept:
            rmv_trips[origMaz][mode] += 1
            rmv_trips[destMaz][mode] += 1

    return all_trips, rmv_trips


def map_removed_trips_by_region(database: SqliteUtil, savepaths: str,
        bounds: List[List[float]] = None):
    log.info('Mapping removed trips by region.')
    cols = ('vehicle', 'transit', 'bike', 'walk')
    
    log.info('Retrieving ABM trip data.')
    all_trips, rmv_trips = fetch_trips(database)

    log.info('Retrieving region data.')
    regions = fetch_regions(database)

    def dump_trips():
        for maz, polygon in regions:
            modes = []
            for rmv, total in zip(rmv_trips[maz], all_trips[maz]):
                modes.append(rmv / total if total > 0 else 0)
            yield (maz, *modes, polygon)

    df = pd.DataFrame(dump_trips(), 
        columns=('maz', 'vehicle', 'transit', 'walk', 'bike', 'region'))
    df['region'] = gpd.GeoSeries(df['region'], crs='epsg:2223')
    gpdf = gpd.GeoDataFrame(df, geometry='region', crs='epsg:2223')

    log.info('Plotting figures.')

    for savepath, bound in zip(savepaths, bounds):
        fig = plt.figure(figsize=(20, 12))
        grid = ImageGrid(
            fig, 111, 
            nrows_ncols=(2,2),
            axes_pad=0.40,
            share_all=True,
            cbar_location="right",
            cbar_mode="single",
            cbar_size="2%",
            cbar_pad=0.25,
        )

        for ax, col in zip(grid, cols):
            plot = gpdf.plot(column=col, cmap='Blues', 
                linewidth=0, ax=ax, alpha=0.5)
            ax.set_title(f'{col} trips')
            if bounds is not None:
                ax.set_xlim(bound[0], bound[2])
                ax.set_ylim(bound[1], bound[3])
            ctx.add_basemap(plot, source=ctx.providers.Stamen.TonerLite, 
                attribution='', crs='epsg:2223')
            vmin = gpdf[col].min()
            vmax = gpdf[col].max()
            sm = plt.cm.ScalarMappable(cmap='Blues', 
                norm=plt.Normalize(vmin=vmin, vmax=vmax))
            sm._A = []

        ax.cax.colorbar(sm)
        ax.cax.toggle_label(True)
        fig.suptitle('portion of trips filtered by mode', 
            x=0.5, y=0.95, fontsize=30, fontweight=5)
        fig.savefig(savepath, dpi=600, bbox_inches='tight')
        plt.clf()


def plot_removed_demographics(database: SqliteUtil, savepath: str):
    log.info('Graphing generated population demographics.')
    log.info('Fetching abm information.')

    query = '''
        SELECT
            persons.age,
            households.hhIncomeDollar,
            persons.persType,
            persons.educLevel,   
            agents.agent_id IS NOT NULL AS kept
        FROM persons
        INNER JOIN households
        ON households.hhid = persons.hhid
        LEFT JOIN agents
        ON persons.hhid = agents.household_id
        AND persons.pnum = agents.household_idx;
    '''
    database.cursor.execute(query)
    result = database.fetch_rows()

    log.info('Building dataframes.')
    cols = ('age', 'income', 'person type', 'education', 'kept')
    df = pd.DataFrame(result, columns=cols)

    fig, axes = plt.subplots(2, 2)
    
    log.info('Plotting age distribution.')
    sns.distplot(df.loc[df['kept'] == 1]['age'], hist=False, color='b', 
        kde_kws={'shade': True}, ax=axes[0,0])
    sns.distplot(df.loc[df['kept'] == 0]['age'], hist=False, color='r', 
        kde_kws={'shade': True}, ax=axes[0,0])
    
    log.info('Plotting income distribution.')
    sns.distplot(df.loc[(df['kept'] == 1) & (df['income'] < 5e5)]['income'], 
        hist=False, color='b', kde_kws={'shade': True}, ax=axes[0,1])
    sns.distplot(df.loc[(df['kept'] == 0) & (df['income'] < 5e5)]['income'], 
        hist=False, color='r',  kde_kws={'shade': True}, ax=axes[0,1])

    log.info('Plotting person type distribution.')
    sns.distplot(df.loc[df['kept'] == 1]['person type'], hist=True, color='b', 
        ax=axes[1,0], kde=True)
    sns.distplot(df.loc[df['kept'] == 0]['person type'], hist=True, color='r', 
        ax=axes[1,0], kde=True)

    log.info('Plotting education level distribution.')
    sns.distplot(df.loc[df['kept'] == 1]['education'], hist=True, color='b', 
        ax=axes[1,1], kde=True)
    sns.distplot(df.loc[df['kept'] == 0]['education'], hist=True, color='r', 
        ax=axes[1,1], kde=True)
    
    log.info('Saving figure.')
    fig.savefig(savepath, bbox_inches='tight')
    plt.clf()   
    


if __name__ == '__main__':
    parser = ArgumentParser('link exposure visualizer')
    
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

    path = lambda x: os.path.abspath(os.path.join(args.dir, x))
    os.makedirs(path('result/maps/'), exist_ok=True)
    os.makedirs(path('result/boxplots/'), exist_ok=True)
    database = SqliteUtil(path('database.db'), readonly=True)


    savepaths = [
        path('result/maps/filtered_trips_by_mode_tempe.png'),
        path('result/maps/filtered_trips_by_mode_phoenix.png')
    ]
    bounds = [
        [ 681285.59126194, 868244.11666725, 710778.10020630, 888780.96744007 ],
        [ 538469.71851555, 820213.86426396, 795753.75497050, 978336.65984825 ]
    ]
    # map_removed_trips_by_region(database, savepaths, bounds)

    savepath = path('result/boxplots/filtered_demographics.png')
    plot_removed_demographics(database, savepath)

