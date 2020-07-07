
import seaborn as sns
import pandas as pd

from icarus.util.sqlite import SqliteUtil


def main(database: SqliteUtil):

    query = '''
        SELECT
            households.hhIncomeDollar,
            output_agents.exposure
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
        adj = (income // 10000) * 10000
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
        y=data['average exposure (°C·sec)'], 
        color='royalblue'
    )
    axes.set_title('Exposure By Income')
    
    for ind, label in enumerate(axes.get_xticklabels()):
        if ind % 10 == 0:
            label.set_visible(True)
        else:
            label.set_visible(False)

    plot = axes.get_figure()

    plot.savefig('result/income_exposure.png', bbox_inches='tight')
    plot.clf()


if __name__ == '__main__':
    database = SqliteUtil('database.db', readonly=True)
    main(database)