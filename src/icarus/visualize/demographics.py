
import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
import logging as log

from argparse import ArgumentParser

from icarus.util.sqlite import SqliteUtil


def plot_income(database: SqliteUtil):
    query = '''
        SELECT
            households.hhIncomeDollar,
            output_agents.exposure / 60
        FROM households
        INNER JOIN agents
        ON households.hhid = agents.household_id
        INNER JOIN output_agents
        ON agents.agent_id = output_agents.agent_id
        WHERE households.hhIncomeDollar < 500000;
    '''

    database.cursor.execute(query)
    persons = database.fetch_rows()
    total = {}
    data = []

    for income, exposure in persons:
        adj = (income // 20000) * 20000
        if adj in total:
            total[adj][0] += exposure
            total[adj][1] += 1
        else:
            total[adj] = [exposure, 1]
        
    for age, (total, count) in total.items():
        data.append((age, total / count))


    data = pd.DataFrame(data, 
        columns=('household income (USD)', 'average exposure (°C·sec)'))
    axes = sns.barplot(
        x=data['household income (USD)'], 
        y=data['average exposure (°C·min)']
    )
    axes.set_title('Exposure By Income')
    
    for ind, label in enumerate(axes.get_xticklabels()):
        if ind % 10 == 0:
            label.set_visible(True)
        else:
            label.set_visible(False)

    plot = axes.get_figure()
    plot.savefig('result/barplots/income_exposure.png', bbox_inches='tight')
    plot.clf()


def plot_age(database: SqliteUtil):
    query = '''
        SELECT
            agents.agent_id,
            persons.age,
            output_agents.exposure / 60
        FROM persons
        INNER JOIN agents
        ON persons.hhid = agents.household_id
        AND persons.pnum = agents.household_idx
        INNER JOIN output_agents
        ON agents.agent_id = output_agents.agent_id;
    '''

    database.cursor.execute(query)
    persons = database.fetch_rows()
    total = {}
    data = []

    for _, age, exposure in persons:
        adj = (age // 5) * 5
        if adj in total:
            total[adj][0] += exposure
            total[adj][1] += 1
        else:
            total[adj] = [exposure, 1]

    for age, (total, count) in total.items():
        data.append((age, total / count))
    
    data = pd.DataFrame(data, columns=('age (years)', 'average exposure (°C·sec)'))
    axes = sns.barplot(
        x=data['age (years)'], 
        y=data['average exposure (°C·min)']
    )
    axes.set_title('Exposure By Age')

    plot = axes.get_figure()
    plot.savefig('result/barplots/age_exposure.png', bbox_inches='tight')
    plot.clf()


def plot_all(database: SqliteUtil):
    log.info('Plotting exposure by demographics.')
    log.info('Fetching agent data.')
    query = '''
        SELECT
            agents.agent_id,
            households.hhIncomeDollar,
            persons.age,
            persons.persType,
            persons.educLevel,
            output_agents.exposure / 60
        FROM persons
        INNER JOIN households
        ON households.hhid = agents.household_id
        INNER JOIN agents
        ON persons.hhid = agents.household_id
        AND persons.pnum = agents.household_idx
        INNER JOIN output_agents
        ON agents.agent_id = output_agents.agent_id;
    '''
    database.cursor.execute(query)
    result = database.fetch_rows()

    def get_age(age):
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

    def get_income(income):
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

    def get_education(education):
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

    # def get_person_type(person_type):
    #     label = None
    #     if person_type in (1,):
    #         label = 1
    #     elif person_type in (2,):
    #         label = 2
    #     elif person_type in (3,):
    #         label = 3
        

    def extract_agents():
        for uuid, income, age, person_type, education, exposure in result:
            yield (uuid, get_income(income), get_age(age), person_type,
                get_education(education), exposure)

    log.info('Building dataframes.')
    cols = ('uuid', 'income', 'age', 'person type', 'education type', 'exposure')
    df = pd.DataFrame(extract_agents(), columns=cols)

    log.info('Plotting figures.')
    fig, axes = plt.subplots(1, 4, 'none', 'all')
    fig.set_size_inches(14, 5)

    sns.boxplot(x='age', y='exposure', ax=axes[0], data=df, fliersize=0, 
        order=('<20', '20-30', '30-60', '>60'))
    axes[0].set_ylim(-1000, 40000)
    sns.boxplot(x='income', y='exposure', ax=axes[1], data=df, fliersize=0,
        order=('<30k', '30-60k', '60-120k', '>120k'))
    axes[1].set_ylim(-1000, 40000)
    axes[1].set_ylabel('')
    sns.boxplot(x='person type', y='exposure', ax=axes[2], data=df, fliersize=0)
    axes[2].set_ylim(-1000, 40000)
    axes[2].set_ylabel('')
    sns.boxplot(x='education type', y='exposure', ax=axes[3], data=df, fliersize=0)
    axes[3].set_ylim(-1000, 40000)
    axes[3].set_ylabel('')

    log.info('Combining and saving figures.')
    fig.suptitle('Exposure Distribution by Demographics')
    fig.savefig('result/boxplots/exposure_by_demographics.png', bbox_inches='tight')
    plt.clf()



def main():
    parser = ArgumentParser('exposure by demographics visualizer')
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
    log.basicConfig()
    # plot_age(database)
    # plot_income(database)
    plot_all(database)


if __name__ == '__main__':
    main()