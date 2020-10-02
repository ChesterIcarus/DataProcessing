
import os
import pandas as pd
import seaborn as sns
import logging as log
import geopandas as gpd
import matplotlib.pyplot as plt

from typing import Tuple, Callable
from argparse import ArgumentParser, SUPPRESS
from icarus.util.apsw import Database
from icarus.util.sqlite import SqliteUtil


def attempt_plot(func: Callable) -> Callable:
    def attempt(*args, **kwargs) -> bool:
        success = True
        try:
            func(*args, **kwargs)
        except Exception as err:
            log.error('Failed to execute "%s".', func.__name__)
            log.error(err)
            success = False
        return success

    return attempt


def cast_age(age: int):
    label = None
    if age < 18:
        label = '<20'
    elif age < 30:
        label = '20-30'
    elif age < 60:
        label = '30-60'
    else:
        label = '>60'
    return label


def cast_income(income: float):
    label = None
    if income < 30000:
        label = '<30k'
    elif income < 60000:
        label = '30-60k'
    elif income < 120000:
        label = '60-120k'
    else:
        label = '>120k'
    return label


def cast_education(education:int):
    label = None
    if education in (0,1,2,3,4,5,6,7,8):
        label = 0
    elif education in (9,):
        label = 1
    elif education in (10, 11):
        label = 2
    elif education in (12, 13):
        label = 3
    else:
        label = 4
    return label


# def load_links(database: SqliteUtil):
#     query = '''
#         SELECT
#             links.link_id,
#             links.length,
#             links.freespeed,
#             links.capacity,
#             links.permlanes,
#             links.modes
#     '''


def load_agents(database: SqliteUtil):
    query = '''
        SELECT
            agents.agent_id,
            agents.uses_vehicle,
            agents.uses_walk,
            agents.uses_bike,
            agents.uses_transit,
            agents.uses_party,
            agents.abort,
            households.hhIncomeDollar,
            persons.age,
            persons.persType,
            persons.educLevel,
            agents.exposure,
            SUM(activities.sim_end - activities.sim_start),
            SUM(legs.sim_end - legs.sim_start),
            SUM(legs.sim_end - legs.sim_start) FILTER(WHERE legs.mode = "walk"),
            SUM(legs.exposure) FILTER(WHERE legs.mode = "walk"),
            SUM(legs.sim_end - legs.sim_start) FILTER(WHERE legs.mode = "bike"),
            SUM(legs.exposure) FILTER(WHERE legs.mode = "bike")
        FROM persons
        INNER JOIN households
        ON households.hhid = agents.household_id
        INNER JOIN agents
        ON persons.hhid = agents.household_id
        AND persons.pnum = agents.household_idx
        INNER JOIN activities
        ON agents.agent_id = activities.agent_id
        INNER JOIN legs
        ON agents.agent_id = legs.agent_id
        GROUP BY agents.agent_id;
    '''
    database.cursor.execute(query)

    cols = (
        'uuid', 'uses_vehicle', 'uses_walk', 'uses_bike', 'uses_transit',
        'uses_party', 'abort', 'income', 'age', 'type', 'education', 
        'exposure', 'act_time', 'leg_time', 'walk_time', 'walk_exp', 
        'bike_time', 'bike_exp'
    )
    df = pd.DataFrame(database.cursor.fetchall(), columns=cols)
    df = df.fillna(0)

    return df


def load_legs(database: SqliteUtil):
    pass


@attempt_plot
def plot_exposure_vs_walk_bike_time(agents: pd.DataFrame, filepath: str, 
        bounds: Tuple[float] = None, title: str = None):
    if title is None:
        title = 'agent exposure vs outdoor travel time'
    
    agents = agents.query('abort == 0 and (uses_walk == 1 or uses_bike == 1)')
    agents = agents.fillna(0)
    exp = agents['exposure'] / 60
    time = (agents['walk_time'] + agents['bike_time']) / 60

    fig = plt.figure(figsize=(6, 5))
    ax = plt.subplot(111)
    sns.scatterplot(x=time, y=exp, alpha=0.3, ax=ax, size=0, legend=False)
    ax.set_ylabel('agent exposure (°C·min)')
    ax.set_xlabel('agent walking/biking time (min)')
    ax.set_title(title)

    if bounds is not None:
        ax.set_xlim(bounds[0], bounds[2])
        ax.set_ylim(bounds[1], bounds[3])

    plt.tight_layout()
    fig.savefig(filepath, bbox_inches='tight', dpi=300)
    fig.clf()


@attempt_plot
def plot_exposure_vs_demographics(agents: pd.DataFrame, filepath: str, 
        bounds: Tuple[float] = None, offset: int = 0, title: str = None):
    if title is None:
        title = 'exposure distribution by demographics'
    
    agents = agents.query('abort == 0')
    agents['age'] = agents['age'].map(cast_age)
    agents['income'] = agents['income'].map(cast_income)
    agents['education'] = agents['education'].map(cast_education)
    
    cast_exposure = lambda x: (x + offset) / 60
    agents['exposure'] = agents['exposure'].map(cast_exposure)
    
    fig, axes = plt.subplots(1, 4, 'none', 'all')
    fig.set_size_inches(10, 4)
    
    sns.boxplot(x='age', y='exposure', ax=axes[0], data=agents, 
        fliersize=0, order=('<20', '20-30', '30-60', '>60'))
    sns.boxplot(x='income', y='exposure', ax=axes[1], data=agents, 
        fliersize=0, order=('<30k', '30-60k', '60-120k', '>120k'))
    sns.boxplot(x='type', y='exposure', ax=axes[2], 
        data=agents, fliersize=0)
    sns.boxplot(x='education', y='exposure', ax=axes[3], 
        data=agents, fliersize=0)

    if bounds is not None:
        axes[0].set_ylim(*bounds)
        axes[1].set_ylim(*bounds)
        axes[2].set_ylim(*bounds)
        axes[3].set_ylim(*bounds)

    axes[1].set_ylabel('')
    axes[2].set_ylabel('')
    axes[3].set_ylabel('')

    fig.suptitle(title, y=1)
    plt.tight_layout()
    fig.savefig(filepath, bbox_inches='tight', dpi=300)
    plt.clf()



def main():
    desc = (
        'A general visualization tool for the icarus output.'
    )
    parser = ArgumentParser('icarus.visualize.general', description=desc, add_help=False)

    custom = parser.add_argument_group('custom options')
    custom.add_argument('--debug', action='load_true', dest='debug', default=False,
        help='add breakpoint after execution; good for debugging')

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
    os.makedirs(path('visuals/output/'), exist_ok=True)

    homepath = path('')
    logpath = path('logs/visualize.log')
    dbpath = path('database.db')

    handlers = []
    handlers.append(log.StreamHandler())
    handlers.append(log.FileHandler(logpath, 'w'))
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

    log.info('Running visualization module.')
    log.info(f'Loading data from {homepath}.')
    log.info('Verifying process metadata/conditions.')

    log.info('Loading agent data from database.')
    database = SqliteUtil(dbpath, readonly=True)
    agents = load_agents(database)

    log.info('Plotting exposure versus walk and bike time.')
    savepath = path('visuals/exposure_vs_walk_bike_time.png')
    bounds = None
    plot_exposure_vs_walk_bike_time(agents, savepath, bounds)

    log.info('Plotting exposure versus walk and bike time (trimmed).')
    savepath = path('visuals/exposure_vs_walk_bike_time_trimmed.png')
    bounds = (-100, 42000, 2000, 46000)
    plot_exposure_vs_walk_bike_time(agents, savepath, bounds)

    log.info('Plotting exposure versus population demographics.')
    savepath = path('visuals/exposure_vs_demographics.png')
    bounds = None
    plot_exposure_vs_demographics(agents, savepath, bounds)

    log.info('Plotting exposure versus population demographics (trimmed).')
    savepath = path('visuals/exposure_vs_demographics_trimmed.png')
    bounds = (42850, 43350)
    plot_exposure_vs_demographics(agents, savepath, bounds, title='')

    log.info('Plotting exposure versus bikiung/walking population demographics.')
    sample = agents.query('uses_bike == 1 or uses_walk == 1')
    savepath = path('visuals/exposure_vs_demographics_bike_walk.png')
    bounds = None
    plot_exposure_vs_demographics(sample, savepath, bounds)

    log.info('Plotting exposure versus biki3ng/walking '
        'population demographics (trimmed).')
    sample = agents.query('uses_bike == 1 or uses_walk == 1')
    savepath = path('visuals/exposure_vs_demographics_bike_walk_trimmed.png')
    bounds = (42400, 44500)
    plot_exposure_vs_demographics(sample, savepath, bounds)

    if args.debug:
        breakpoint()


if __name__ == '__main__':
    main()
