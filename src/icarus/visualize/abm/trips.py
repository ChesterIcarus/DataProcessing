
import os
import pandas as pd
import seaborn as sns
import logging as log
import matplotlib.pyplot as plt

from typing import Callable
from argparse import ArgumentParser, SUPPRESS

from icarus.util.sqlite import SqliteUtil


def plot_trip_dist_all(database: SqliteUtil, path: Callable[[str],str]):
    log.info('Fetching abm trip data.')
    query = '''
        SELECT
            nmode,
            freq,
            COUNT(*)
        FROM (
            SELECT 
                COUNT(*) AS freq,
                CASE
                    WHEN mode = 11 THEN "walk"
                    WHEN mode IN (1, 2, 3, 4, 13, 14) THEN "vehicle"
                    WHEN mode IN (5, 6, 7, 8, 9, 10) THEN "transit"
                    WHEN mode = 12 THEN "bike"
                    ELSE NULL 
                    END AS nmode 
            FROM trips
            GROUP BY hhid, pnum, nmode
        ) AS counts
        GROUP BY nmode, freq
        ORDER BY nmode, freq ASC;
    '''
    database.cursor.execute(query)

    log.info('Building dataframe.')
    cols = ('mode', 'bin', 'count')
    df = pd.DataFrame(database.fetch_rows(), columns=cols)
    
    log.info('Plotting abm walk trip dist.')
    data = df.loc[df['mode'] == 'walk']
    ax = sns.barplot(x=data['bin'], y=data['count'])
    ax.set_xlabel('number of trips')
    ax.set_ylabel('number of persons')
    ax.set_title('Person Count By Walking Trip Count')
    savepath = path('visuals/abm/trips_walk.png')
    fig = ax.get_figure()
    fig.tight_layout()
    fig.savefig(savepath, bbox_inches='tight')
    plt.clf()
    del data

    log.info('Plotting abm vehicle trip dist.')
    data = df.loc[df['mode'] == 'vehicle']
    ax = sns.barplot(x=data['bin'], y=data['count'])
    ax.set_xlabel('number of trips')
    ax.set_ylabel('number of persons')
    ax.set_title('Person Count By Vehicle Trip Count')
    savepath = path('visuals/abm/trips_vehicle.png')
    fig = ax.get_figure()
    fig.tight_layout()
    fig.savefig(savepath, bbox_inches='tight')
    plt.clf()
    del data

    log.info('Plotting abm transit trip dist.')
    data = df.loc[df['mode'] == 'transit']
    ax = sns.barplot(x=data['bin'], y=data['count'])
    ax.set_xlabel('number of trips')
    ax.set_ylabel('number of persons')
    ax.set_title('Person Count By Transit Trip Count')
    savepath = path('visuals/abm/trips_transit.png')
    fig = ax.get_figure()
    fig.tight_layout()
    fig.savefig(savepath, bbox_inches='tight')
    plt.clf()
    del data

    log.info('Plotting abm bike trip dist.')
    data = df.loc[df['mode'] == 'bike']
    ax = sns.barplot(x=data['bin'], y=data['count'])
    ax.set_xlabel('number of trips')
    ax.set_ylabel('number of persons')
    ax.set_title('Person Count By Bike Trip Count')
    savepath = path('visuals/abm/trips_bike.png')
    fig = ax.get_figure()
    fig.tight_layout()
    fig.savefig(savepath, bbox_inches='tight')
    plt.clf()
    del data


def main():
    desc = (
        ''
    )
    parser = ArgumentParser('icarus.visualize.abm.trips', 
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
    logpath = path('logs/visualize_abm_trips.log')
    dbpath = path('database.db')
    os.makedirs(path('logs'), exist_ok=True)
    os.makedirs(path('visuals/abm/'), exist_ok=True)

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

    plot_trip_dist_all(database, path)


if __name__ == '__main__':
    main()
