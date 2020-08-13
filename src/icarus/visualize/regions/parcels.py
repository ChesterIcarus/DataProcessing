
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


def main():
    desc = (
        ''
    )
    parser = ArgumentParser('icarus.visualize.regions.parcels',
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

    logpath = path('logs/visualize_regions_parcels.log')
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
    plot_parcels_map_all(database, path, bounds)


if __name__ == '__main__':
    main()