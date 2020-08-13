
import os
import numpy as np
import pandas as pd
import seaborn as sns
import logging as log
import matplotlib.pyplot as plt

from typing import Callable
from argparse import ArgumentParser, SUPPRESS

from icarus.util.sqlite import SqliteUtil


def plot_demographics_all(database: SqliteUtil, path: Callable[[str], str]):
    log.info('Beginning plotting of all abm demographics.')

    log.info('Fetching abm information.')
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
    ax = sns.distplot(df['age'], hist=False, kde_kws={'shade': True})
    ax.set_xlabel('age')
    ax.set_ylabel('proportion of persons')
    ax.set_title('ABM age distribution')
    savepath = path('visuals/abm/demographics_age.png')
    fig = ax.get_figure()
    fig.savefig(savepath, bbox_inches='tight')
    plt.clf()

    log.info('Plotting income distribution.')
    ax = sns.distplot(df.loc[df['income'] < 5e5]['income'],
        hist=False, kde_kws={'shade': True})
    ax.set_xlabel('income')
    ax.set_ylabel('proportion of persons')
    ax.set_title('ABM income distribution')
    savepath = path('visuals/abm/demographics_income.png')
    fig = ax.get_figure()
    fig.savefig(savepath, bbox_inches='tight')
    plt.clf()

    log.info('Plotting education distribution.')
    series = df['education'].value_counts().sort_index()
    values = np.array(series.index.array)
    total = sum(series.array)
    apply = lambda x: x / total 
    proportion = np.array(tuple(map(apply, series.array)))
    ax = sns.barplot(x=values, y=proportion)
    ax.set_xlabel('education')
    ax.set_ylabel('proportion of persons')
    ax.set_title('ABM education distribution')
    savepath = path('visuals/abm/demographics_education.png')
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
    ax = sns.barplot(x=values, y=proportion)
    ax.set_xlabel('person type')
    ax.set_ylabel('proportion of persons')
    ax.set_title('ABM person type distribution')
    savepath = path('visuals/abm/demographics_persontype.png')
    fig = ax.get_figure()
    fig.savefig(savepath, bbox_inches='tight')
    plt.clf()
    del values, total, apply, proportion

    log.info('Plotting joint plot.')
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(10, 6))
    
    log.info('Adding age distribution.')
    sns.distplot(df['age'], hist=False, kde_kws={'shade': True}, ax=ax1)
    
    log.info('Addding income distribution.')
    sns.distplot(df.loc[df['income'] < 5e5]['income'],
        hist=False, kde_kws={'shade': True}, ax=ax2)

    log.info('Adding education distribution.')
    series = df['education'].value_counts().sort_index()
    values = np.array(series.index.array)
    total = sum(series.array)
    apply = lambda x: x / total 
    proportion = np.array(tuple(map(apply, series.array)))
    sns.barplot(x=values, y=proportion, ax=ax3)
    del values, total, apply, proportion

    log.info('Adding person type distribution.')
    series = df['person type'].value_counts().sort_index()
    values = np.array(series.index.array)
    total = sum(series.array)
    apply = lambda x: x / total 
    proportion = np.array(tuple(map(apply, series.array)))
    sns.barplot(x=values, y=proportion, ax=ax4)
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

    fig.suptitle('ABM population demographics', y=1)
    savepath = path('visuals/abm/demographics_all.png')
    fig.savefig(savepath, bbox_inches='tight')
    plt.clf()


def main():
    desc = (
        ''
    )
    parser = ArgumentParser('icarus.visualize.abm.demographics', 
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
    logpath = path('logs/visualize_abm_demographics.log')
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

    plot_demographics_all(database, path)


if __name__ == '__main__':
    main()
