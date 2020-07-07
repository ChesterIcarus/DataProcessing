
import seaborn as sns
import pandas as pd

from icarus.util.sqlite import SqliteUtil


def main(database: SqliteUtil):
    query = '''
        SELECT
            agents.agent_id,
            persons.age,
            output_agents.exposure
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
    axes = sns.barplot(x=data['age (years)'], y=data['average exposure (°C·sec)'], color='royalblue')
    axes.set_title('Exposure By Age')
    plot = axes.get_figure()

    plot.savefig('result/age_exposure.png', bbox_inches='tight')
    plot.clf()


if __name__ == '__main__':
    database = SqliteUtil('database.db', readonly=True)
    main(database)
        