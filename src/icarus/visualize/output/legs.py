
import os
import pandas as pd
import logging as log
import seaborn as sns
import matplotlib.pyplot as plt
from argparse import ArgumentParser

from icarus.util.sqlite import SqliteUtil


def get_leg_differentials(database, parameter, bounds, sample, modes):
    conds = []
    if modes is not None:
        if len(modes) > 1:
            conds.append(f'legs.mode IN {tuple(modes)}')
        else:
            conds.append(f'legs.mode = "{modes[0]}"')
    # if bounds is not None:
    #     conds.append(f'legs.{parameter} >= {bounds[0] * 60}')
    #     conds.append(f'output_legs.{parameter} >= {bounds[1] * 60}')
    #     conds.append(f'legs.{parameter} <= {bounds[2] * 60}')
    #     conds.append(f'output_legs.{parameter} <= {bounds[3] * 60}')
    
    conds.append('legs.abort = 0')

    condition = 'WHERE ' + ' AND '.join(conds) if len(conds) else ''
    limit = f'ORDER BY RANDOM() LIMIT {sample}' if sample is not None else ''

    query = f'''
        SELECT 
            (legs.abm_end - legs.abm_start) / 60.0,
            (legs.sim_end - legs.sim_start) / 60.0
        FROM legs
        {condition}
        {limit};
    '''    
    database.cursor.execute(query)

    return database.fetch_rows()


def plot_leg_distribution(database, savepath, parameter, bounds, 
        sample, modes, axes, title):
    values = get_leg_differentials(database, parameter, bounds, sample, modes)
    if bounds is not None:
        bound = lambda x: all((x[0] > bounds[0], x[0] < bounds[2], 
                x[1] > bounds[1], x[1] < bounds[3]))
        values = filter(bound, values)
    data = pd.DataFrame(list(values), columns=axes)
    if bounds is None:
        high = max(*data[axes[0]], *data[axes[1]])
        low = min(*data[axes[0]], *data[axes[1]])
    else:
        low = min(bounds[0], bounds[1])
        high = max(bounds[2], bounds[3])
    try:
        plot = sns.jointplot(x=data[axes[0]], y=data[axes[1]], kind='hex')
        fig = plot.fig
        fig.axes[2].plot([low, low], [high, high], linewidth=1.5)
        fig.suptitle(title, y=1)
        fig.tight_layout()

        fig.savefig(savepath, bbox_inches='tight')
        plt.clf()
    except:
        log.error(f'Failed to make plot "{title}".')
    

def plot_leg_differential(database, savepath, parameter, bounds, 
        sample, modes, axes, title):
    values = get_leg_differentials(database, parameter, None, sample, modes)
    values = map(lambda x: x[1] - x[0], values)
    if bounds is not None:
        condition = lambda x: x >= bounds[0] and x <= bounds[1]
        values = filter(condition, values)
    data = pd.Series(values)
    ax = sns.distplot(data)
    ax.set_title(title)
    ax.set_xlabel(axes[0])
    ax.set_ylabel(axes[1])
    fig = ax.get_figure()
    fig.tight_layout()

    fig.savefig(savepath, bbox_inches='tight')
    plt.clf()


def main():
    parser = ArgumentParser('output timing visualization')
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

    database = SqliteUtil(path('database.db'), readonly=True)

    os.makedirs(path('visuals/output/'), exist_ok=True)


    # walking legs distribution
    savepath = path('visuals/output/leg_duration_distrbution_walk.png')
    parameter = 'duration'
    bounds = [ 0, 0, 30, 30 ]
    sample = None
    modes = [ 'walk' ]
    axes = [ 'ABM leg duration (min)', 'MATSim leg duration (min)' ]
    title = 'Leg Durations (Walking)'
    plot_leg_distribution(database, savepath, parameter, bounds, 
        sample, modes, axes, title) 
    
    # walking legs distribution
    savepath = path('visuals/output/leg_duration_differential_walk.png')
    parameter = 'duration'
    bounds = [ -30, 30 ]
    sample = None
    modes = [ 'walk' ]
    axes = [ 
        'Difference in Simulated and ABM Leg Duration (min)', 
        'Frequency' 
    ]
    title = 'Leg Durations (Walking)'
    plot_leg_differential(database, savepath, parameter, bounds, 
        sample, modes, axes, title)

    # biking legs distribution
    savepath = path('visuals/output/leg_duration_distrbution_bike.png')
    parameter = 'duration'
    bounds = [ 0, 0, 30, 30 ]
    sample = None
    modes = [ 'bike' ]
    axes = [ 'ABM leg duration (min)', 'MATSim leg duration (min)' ]
    title = 'Leg Durations (Biking)'
    plot_leg_distribution(database, savepath, parameter, bounds, 
        sample, modes, axes, title) 
    
    # biking legs distribution
    savepath = path('visuals/output/leg_duration_differential_bike.png')
    parameter = 'duration'
    bounds = [ -30, 30 ]
    sample = None
    modes = [ 'bike' ]
    axes = [ 
        'Difference in Simulated and ABM Leg Duration (min)', 
        'Frequency' 
    ]
    title = 'Leg Durations (Biking)'
    plot_leg_differential(database, savepath, parameter, bounds, 
        sample, modes, axes, title)

    # vehicle legs distribution
    savepath = path('visuals/output/leg_duration_distrbution_vehicle.png')
    parameter = 'duration'
    bounds = [ 0, 0, 30, 30 ]
    sample = None
    modes = [ 'car' ]
    axes = [ 'ABM leg duration (min)', 'MATSim leg duration (min)' ]
    title = 'Leg Durations (Vehicle)'
    plot_leg_distribution(database, savepath, parameter, bounds, 
        sample, modes, axes, title) 
    
    # biking legs distribution
    savepath = path('visuals/output/leg_duration_differential_vehicle.png')
    parameter = 'duration'
    bounds = [ -30, 30 ]
    sample = None
    modes = [ 'car' ]
    axes = [ 
        'Difference in Simulated and ABM Leg Duration (min)', 
        'Frequency' 
    ]
    title = 'Leg Durations (Vehicle)'
    plot_leg_differential(database, savepath, parameter, bounds, 
        sample, modes, axes, title)


if __name__ == '__main__':
    main()