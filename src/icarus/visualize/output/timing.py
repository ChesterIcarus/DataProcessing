
import os
import pandas as pd
import logging as log
import seaborn as sns
import matplotlib.pyplot as plt
from argparse import ArgumentParser

from icarus.util.sqlite import SqliteUtil


# def get_activity_differentials(database, parameter, bounds, sample, types):
#     conds = []
#     if types is not None:
#         if len(types) > 1:
#             conds.append(f'output_activities.type IN {tuple(types)}')
#         else:
#             conds.append(f'output_activities.type = {types[0]}')
#     if bounds is not None:
#         conds.append(f'activities.{parameter} >= {bounds[0]}')
#         conds.append(f'output_activities.{parameter} >= {bounds[1]}')
#         conds.append(f'activities.{parameter} <= {bounds[2]}')
#         conds.append(f'output_activities.{parameter} <= {bounds[3]}')

#     condition = 'WHERE ' + ' AND '.join(conds) if len(conds) else ''
#     limit = f'LIMIT {sample}' if sample is not None else ''

#     query = f'''
#         SELECT 
#             activities.{parameter},
#             output_activities.{parameter} / 60.0
#         FROM activities
#         INNER JOIN output_activities
#         USING(agent_id, agent_idx)
#         {condition}
#         ORDER BY RANDOM()
#         {limit}; '''

#     database.cursor.execute(query)

#     return database.fetch_rows()


def get_leg_differentials(database, parameter, bounds, sample, modes):
    conds = []
    if modes is not None:
        if len(modes) > 1:
            conds.append(f'output_legs.mode IN {tuple(modes)}')
        else:
            conds.append(f'output_legs.mode = "{modes[0]}"')
    if bounds is not None:
        conds.append(f'legs.{parameter} >= {bounds[0] * 60}')
        conds.append(f'output_legs.{parameter} >= {bounds[1] * 60}')
        conds.append(f'legs.{parameter} <= {bounds[2] * 60}')
        conds.append(f'output_legs.{parameter} <= {bounds[3] * 60}')
    
    conds.append('output_legs.abort = 0')

    condition = 'WHERE ' + ' AND '.join(conds) if len(conds) else ''
    limit = f'LIMIT {sample}' if sample is not None else ''

    query = f'''
        SELECT 
            legs.{parameter} / 60.0,
            output_legs.{parameter} / 60.0
        FROM legs
        INNER JOIN output_legs
        USING(agent_id, agent_idx)
        {condition}
        ORDER BY RANDOM()
        {limit};    '''        
    
    database.cursor.execute(query)

    return database.fetch_rows()


# def plot_activity_distribution(database, savepath, parameter, bounds, 
#         sample, types, axes, title):
#     values = get_activity_differentials(database, parameter, bounds, sample, types)
#     data = pd.DataFrame(list(values), columns=axes)
#     high = max(*data[axes[0]], *data[axes[1]])
#     low = min(*data[axes[0]], *data[axes[1]])
#     plot = sns.jointplot(
#         x=data[axes[0]], 
#         y=data[axes[1]], kind='hex').fig
#     plot.axes[2].plot([low, low], [high, high], linewidth=1.5)
#     plot.subplots_adjust(top=0.95)
#     plot.suptitle(title)

#     return plot


def plot_leg_distribution(database, savepath, parameter, bounds, 
        sample, modes, axes, title):
    values = get_leg_differentials(database, parameter, bounds, sample, modes)
    data = pd.DataFrame(list(values), columns=axes)
    if bounds is None:
        high = max(*data[axes[0]], *data[axes[1]])
        low = min(*data[axes[0]], *data[axes[1]])
    else:
        low = min(bounds[0], bounds[1])
        high = max(bounds[2], bounds[3])
    try:
        plot = sns.jointplot(x=data[axes[0]], y=data[axes[1]], kind='hex')
    except:
        breakpoint()
    fig = plot.fig
    fig.axes[2].plot([low, low], [high, high], linewidth=1.5)
    # fig.subplots_adjust(top=1)
    fig.suptitle(title, y=1)
    fig.tight_layout()

    fig.savefig(savepath, bbox_inches='tight')
    plt.clf()
    


# def plot_activity_differential(database, savepath, parameter, bounds, 
#         sample, types, axes, title):
#     values = get_activity_differentials(database, parameter, None, sample, types)
#     values = map(lambda x: x[1] - x[0], values)
#     if bounds is not None:
#         condition = lambda x: x >= bounds[0] and x <= bounds[1]
#         values = filter(condition, values)
#     data = pd.Series(values)
#     plt_axes = sns.distplot(data)
#     plt_axes.set_title(title)
#     plt_axes.set_xlabel(axes[0])
#     plt_axes.set_ylabel(axes[1])
#     plot = plt_axes.get_figure()

#     return plot


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

    os.makedirs(path('result/output/'), exist_ok=True)


    # walking legs distribution
    savepath = path('result/output/leg_duration_distrbution.png')
    parameter = 'duration'
    bounds = [ 0, 0, 30, 30 ]
    sample = None
    modes = [ 'walk' ]
    axes = [ 'ABM leg duration (min)', 'MATSim leg duration (min)' ]
    title = 'Leg Durations (Walking)'
    plot_leg_distribution(database, savepath, parameter, bounds, 
        sample, modes, axes, title) 
    
    # walking legs distribution
    savepath = path('result/output/leg_duration_differential.png')
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


if __name__ == '__main__':
    main()