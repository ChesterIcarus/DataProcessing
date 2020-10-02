
import numpy as np
import pandas as pd
import seaborn as sns
import logging as log
import matplotlib.pyplot as plt

from icarus.util.apsw import Database

# def attempt_plot():


def fetch_links(database: Database) -> pd.DataFrame:
    # query = '''
    #     SELECT
    #         links.link_id,
    #         air_temperatures.temperature_idx,
    #         IFNULL(mrt_temperatures.mrt, air_temperatures.temperature),
    #         air_temperatures.temperature
    #     FROM links
    #     INNER JOIN air_temperatures
    #     ON links.air_temperature = air_temperatures.temperature_id
    #     LEFT JOIN mrt_temperatures
    #     ON links.mrt_temperature = mrt_temperatures.temperature_id
    #     AND air_temperatures.temperature_idx = mrt_temperatures.temperature_idx
    #     WHERE link_id = 1;
    # '''
    # database.cursor.execute(query)

    # cols = ('link_id', 'idx', 'air', 'mrt')
    # rows = database.cursor.fetchall()
    # links = pd.DataFrame(rows, columns=cols)

    query = '''
        SELECT
            air_temperatures.temperature_idx AS idx,
            AVG(IFNULL(mrt_temperatures.mrt, air_temperatures.temperature)) AS mrt,
            AVG(air_temperatures.temperature) AS air
        FROM links
        INNER JOIN air_temperatures
        ON links.air_temperature = air_temperatures.temperature_id
        LEFT JOIN mrt_temperatures
        ON links.mrt_temperature = mrt_temperatures.temperature_id
        AND air_temperatures.temperature_idx = mrt_temperatures.temperature_idx
        GROUP BY idx;
    '''
    database.cursor.execute(query)

    cols = ('idx', 'mrt', 'air')
    rows = database.cursor.fetchall()
    links = pd.DataFrame(rows, columns=cols)

    return links


def plot_averages(links: pd.DataFrame):
    savepath= 'visuals/mrt_vs_daymet_values.png'
    fig = plt.figure()
    ax = plt.subplot(111)

    sns.lineplot(x='idx', y='mrt', data=links, ax=ax)
    sns.lineplot(x='idx', y='air', data=links, ax=ax)

    ax.set_ylabel('temperature (°C)')
    ax.set_xlabel('temperature idx')

    plt.tight_layout()
    fig.savefig(savepath, bbox_inches='tight', dpi=300)
    fig.clf()


def main():
    database = Database('database.db', readonly=True)

    log.basicConfig()

    log.info('Fetching link temperature data from database')
    links = fetch_links(database)

    try:
        plot_averages(links)
    except Exception as err:
        log.error('Plotting average failed.')
        log.error(err)

    breakpoint()


if __name__ == '__main__':
    main()
