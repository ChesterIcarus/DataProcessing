
import os
import numpy as np
import pandas as pd
import seaborn as sns
import logging as log
import geopandas as gpd
import contextily as ctx
import matplotlib.pyplot as plt

from typing import List, Callable
from shapely.wkt import loads
from collections import defaultdict
from argparse import ArgumentParser
from pyproj.transformer import Transformer
from shapely.wkt import loads
from shapely.geometry import Polygon
from mpl_toolkits.axes_grid1 import ImageGrid

from icarus.util.sqlite import SqliteUtil
from icarus.util.general import counter


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
            cbar_location='right',
            cbar_mode='single',
            cbar_size='2%',
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


def plot_demographics_all(database: SqliteUtil, path: Callable[[str], str]):
    log.info('Beginning plotting of all input population demographics.')

    log.info('Fetching input population information.')
    query = ''' 
        SELECT
            persons.age,
            persons.persType,
            persons.educLevel,
            persons.industry,
            persons.gender,
            households.hhIncomeDollar
        FROM persons
        INNER JOIN households
        ON households.hhid = persons.hhid;
    '''
    database.cursor.execute(query)
    result = database.fetch_rows()
    
    log.info('Building dataframe.')
    cols = ('age', 'person type', 'education', 'industry', 'gender', 'income')
    df = pd.DataFrame(result, columns=cols)
    del result

    log.info('Plotting age distribution.')
    ax = sns.distplot(df['age'], hist=False, color='red', 
        kde_kws={'shade': True})
    ax.set_xlabel('age')
    ax.set_ylabel('proportion of persons')
    ax.set_title('input age distribution')
    savepath = path('result/input/demographics_age.png')
    fig = ax.get_figure()
    fig.savefig(savepath, bbox_inches='tight')
    plt.clf()

    log.info('Plotting income distribution.')
    ax = sns.distplot(df.loc[df['income'] < 5e5]['income'],
        hist=False, color='blue', kde_kws={'shade': True})
    ax.set_xlabel('income')
    ax.set_ylabel('proportion of persons')
    ax.set_title('input income distribution')
    savepath = path('result/input/demographics_income.png')
    fig = ax.get_figure()
    fig.savefig(savepath, bbox_inches='tight')
    plt.clf()

    log.info('Plotting education distribution.')
    series = df['education'].value_counts().sort_index()
    values = np.array(series.index.array)
    total = sum(series.array)
    apply = lambda x: x / total 
    proportion = np.array(tuple(map(apply, series.array)))
    ax = sns.barplot(x=values, y=proportion, color='green')
    ax.set_xlabel('education')
    ax.set_ylabel('proportion of persons')
    ax.set_title('input education distribution')
    savepath = path('result/input/demographics_education.png')
    fig = ax.get_figure()
    fig.savefig(savepath, bbox_inches='tight')
    plt.clf()
    del values, total, apply, proportion
    
    log.info('Adding person type distribution.')
    series = df['person type'].value_counts().sort_index()
    values = np.array(series.index.array)
    total = sum(series.array)
    apply = lambda x: x / total 
    proportion = np.array(tuple(map(apply, series.array)))
    ax = sns.barplot(x=values, y=proportion, color='darkviolet')
    ax.set_xlabel('person type')
    ax.set_ylabel('proportion of persons')
    ax.set_title('input person type distribution')
    savepath = path('result/input/demographics_persontype.png')
    fig = ax.get_figure()
    fig.savefig(savepath, bbox_inches='tight')
    plt.clf()
    del values, total, apply, proportion

    log.info('Plotting joint plot.')
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(10, 6))
    
    log.info('Adding age distribution.')
    sns.distplot(df['age'], hist=False, color='red', 
        kde_kws={'shade': True}, ax=ax1)
    
    log.info('Addding income distribution.')
    sns.distplot(df.loc[df['income'] < 5e5]['income'],
        hist=False, color='blue', kde_kws={'shade': True}, ax=ax2)

    log.info('Adding education distribution.')
    series = df['education'].value_counts().sort_index()
    values = np.array(series.index.array)
    total = sum(series.array)
    apply = lambda x: x / total 
    proportion = np.array(tuple(map(apply, series.array)))
    sns.barplot(x=values, y=proportion, color='green', ax=ax3)
    del values, total, apply, proportion

    log.info('Adding person type distribution.')
    series = df['person type'].value_counts().sort_index()
    values = np.array(series.index.array)
    total = sum(series.array)
    apply = lambda x: x / total 
    proportion = np.array(tuple(map(apply, series.array)))
    sns.barplot(x=values, y=proportion, color='darkviolet', ax=ax4)
    del values, total, apply, proportion

    ax1.set_xlabel('age')
    ax2.set_xlabel('income')
    ax3.set_xlabel('education level')
    ax4.set_xlabel('person type')

    fig.add_subplot(111, frameon=False)
    plt.tick_params(labelcolor='none', top=False, 
        bottom=False, left=False, right=False)
    plt.grid(False)
    plt.ylabel('proportion of persons', labelpad=20)
    plt.tight_layout()

    fig.suptitle('input population demographics', y=1)
    savepath = path('result/input/demographics_all.png')
    fig.savefig(savepath, bbox_inches='tight')
    plt.clf()


def plot_removed_demographics(database: SqliteUtil, savepath: str):
    log.info('Graphing generated population demographics.')
    log.info('Fetching abm information.')

    query = '''
        SELECT
            persons.age,
            households.hhIncomeDollar,
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
    cols = ('age', 'income', 'kept')
    df = pd.DataFrame(result, columns=cols)

    fig, (ax1, ax2) = plt.subplots(1, 2)
    
    log.info('Plotting age distribution.')
    sns.distplot(df.loc[df['kept'] == 1]['age'], hist=False, color='b', 
        kde_kws={'shade': True}, ax=ax1, label='input')
    sns.distplot(df['age'], hist=False, color='g', 
        kde_kws={'shade': True}, ax=ax1, label='ABM')
    
    log.info('Plotting income distribution.')
    sns.distplot(df.loc[(df['kept'] == 1) & (df['income'] < 5e5)]['income'], 
        hist=False, color='b', kde_kws={'shade': True}, ax=ax2, label='input')
    sns.distplot(df.loc[df['income'] < 5e5]['income'],
        hist=False, color='g', kde_kws={'shade': True}, ax=ax2, label='ABM')

    log.info('Plotting ')
    
    log.info('Saving figure.')
    fig.add_subplot(111, frameon=False)
    plt.tick_params(labelcolor='none', top=False, bottom=False,
        left=False, right=False)
    plt.grid(False)
    plt.ylabel('proportion of population', labelpad=15)
    plt.tight_layout()

    fig.suptitle('distribution of demographics', y=1)
    fig.savefig(savepath, bbox_inches='tight')
    plt.clf()


def plot_lowerbound_speeds(database: SqliteUtil, savepath: str):
    log.info('Analyzing population lower bound speeds.')
    log.info('Fetching region data.')
    query = '''
        SELECT
            maz,
            region
        FROM regions;
    '''
    database.cursor.execute(query)
    result = database.fetch_rows()

    regions = {}
    for maz, region in result:
        polygon = Polygon(loads(region))
        regions[maz] = polygon

    log.info('Loading trip data.')
    query = '''
        SELECT
            origMaz,
            destMaz,
            mode,
            (isamAdjArrMin - isamAdjDepMin) * 60
        FROM trips;
    ''' 
    database.cursor.execute(query)
    result = database.fetch_rows()
    result = counter(result, 'Analyzing trip %s.', level=log.DEBUG)

    log.info('Calculating lower bound speeds.')
    vehicle = []
    walk = []
    transit = []
    bike = []
    cache = defaultdict(dict)
    for orig_maz, dest_maz, mode, dur in result:
        if dur > 0 and orig_maz in regions and dest_maz in regions:
            if orig_maz == dest_maz:
                speed = 0
            elif orig_maz < dest_maz:
                if dest_maz in cache[orig_maz]:
                    dist = cache[orig_maz][dest_maz]
                else:
                    dist = regions[orig_maz].distance(regions[dest_maz])
                    cache[orig_maz][dest_maz] = dist
                speed = dist / dur * 3600 / 5280
            else:
                if orig_maz in cache[dest_maz]:
                    dist = cache[dest_maz][orig_maz]
                else:
                    dist = regions[dest_maz].distance(regions[orig_maz])
                    cache[dest_maz][orig_maz] = dist
                speed = dist / dur * 3600 / 5280

            if mode in (1,2,3,4,13,14):
                vehicle.append(speed)
            elif mode in (5,6,7,8,9,10):
                transit.append(speed)
            elif mode in (11,):
                walk.append(speed)
            elif mode in (12,):
                bike.append(speed)
    
    del cache

    vehicle.sort()
    walk.sort()
    transit.sort()
    bike.sort()

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, True, True)

    speed = np.array(list(range(0, 110, 10)))
    proportion = np.array([sorted_lte_portion(vehicle, i) for i in speed])
    sns.barplot(x=speed, y=proportion, ax=ax1, color='blue')

    speed = np.array(list(range(0, 110, 10)))
    proportion = np.array([sorted_lte_portion(transit, i) for i in speed])
    sns.barplot(x=speed, y=proportion, ax=ax2, color='green')

    speed = np.array(list(range(0, 110, 10)))
    proportion = np.array([sorted_lte_portion(walk, i) for i in speed])
    sns.barplot(x=speed, y=proportion, ax=ax3, color='red')

    speed = np.array(list(range(0, 110, 10)))
    proportion = np.array([sorted_lte_portion(bike, i) for i in speed])
    sns.barplot(x=speed, y=proportion, ax=ax4, color='darkviolet')

    ax1.set_title('vehicle trips')
    ax2.set_title('transit trips')
    ax3.set_title('walk trips')
    ax4.set_title('bike trips')

    fig.add_subplot(111, frameon=False)
    plt.tick_params(labelcolor='none', top=False, bottom=False,
        left=False, right=False)
    plt.grid(False)
    plt.xlabel('lower bound speed (mph)')
    plt.ylabel('proportion of trips')
    plt.tight_layout()

    fig.suptitle('proportion of trips below lower bound speed by mode', y=1)
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
    os.makedirs(path('result/input/'), exist_ok=True)
    database = SqliteUtil(path('database.db'), readonly=True)

    savepaths = [
        path('result/input/filtered_trips_by_mode_tempe.png'),
        path('result/input/filtered_trips_by_mode_phoenix.png')
    ]
    bounds = [
        [ 681285.59126194, 868244.11666725, 710778.10020630, 888780.96744007 ],
        [ 538469.71851555, 820213.86426396, 795753.75497050, 978336.65984825 ]
    ]
    map_removed_trips_by_region(database, savepaths, bounds)

    # savepath = path('result/boxplots/filtered_demographics.png')
    # plot_removed_demographics(database, savepath)

    plot_demographics_all(database, path)

    savepath = path('result/input/lower_bound_speed.png')
    plot_lowerbound_speeds(database, savepath)

