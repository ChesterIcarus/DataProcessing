
import shapely
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from icarus.util.apsw import Database


def xy(point: str) -> tuple:
    return tuple(map(float, point[7:-1].split(' ')))


def get_route_length(database: Database, mode: str) -> pd.DataFrame:
    query = f'''
        SELECT
            legs.leg_id,
            legs.mode,
            COUNT(*) AS num_links,
            SUM(links.length) / 5280 AS total_length
        FROM legs
        INNER JOIN events
        USING (leg_id)
        INNER JOIN links
        USING (link_id)
        WHERE legs.mode = "{mode}"
        GROUP BY legs.leg_id;
    '''

    with database.connection:
        database.cursor.execute(query)
        cols = ('uuid', 'mode', 'count', 'length')
        rows = database.cursor.fetchall()

    df = pd.DataFrame(rows, columns=cols)

    return df


def get_route_teleportation(database: Database, mode: str) -> pd.DataFrame:
    query = f'''
        SELECT
            legs.leg_id,
            nodes.point,
            parcels.center
        FROM legs
        INNER JOIN events
        USING (leg_id)
        INNER JOIN links AS links
        USING (link_id)
        INNER JOIN nodes
        ON nodes.node_id = links.terminal_node
        INNER JOIN activities
        ON legs.agent_id = activities.agent_id
        AND legs.agent_idx + 1 = activities.agent_idx
        INNER JOIN parcels
        USING (apn)
        WHERE event_id = (
            SELECT MAX(event_id)
            FROM events
            WHERE leg_id = legs.leg_id
        )
        AND mode = "{mode}";
    '''

    rows = []
    with database.connection:
        result = database.cursor.execute(query)
        for uuid, link, parcel in result:
            x1, y1 = xy(link)
            x2, y2 = xy(parcel)
            d = ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
            rows.append((uuid, x2, y2, d))

    cols = ('uuid', 'lat', 'lon', 'distance')
    df = pd.DataFrame(rows, columns=cols)

    return df


def get_route_time_activity(database: Database) -> pd.DataFrame:
    query = f'''
        SELECT
            mode,
            sim_start,
            sim_end
        FROM legs
        WHERE (
            mode = "walk"
            OR mode = "bike"
        )
        AND ABORT = 0;
    '''

    rows = []
    with database.connection:
        result = database.cursor.execute(query)    
        for mode, start, end in result:
            first = int(start / 3600)
            last = int(end / 3600)

            if first == last:
                rows.append((first, end - start, mode))
            else:
                rows.append((first, (first + 1) * 3600 - start, mode))
                rows.append((last, end - last * 3600, mode))

            for hour in range(first + 1, last):
                rows.append((hour, 3600, mode))

    
    cols = ('hour', 'duration', 'mode')
    df = pd.DataFrame(rows, columns=cols)

    return df


def plot_route_lengths(database: Database):
    print('Fetching walking routes.')

    df = get_route_length(database, 'walk')

    print('Plotting walking route link count pdf.')

    df1 = df.query('count <= 100')

    fig = plt.figure()
    ax = plt.subplot(111)
    sns.histplot(data=df1, x='count', ax=ax, stat='count', kde=True)
    ax.set_xlabel('links')
    ax.set_ylabel('routes')
    ax.set_title('walking route link count')
    plt.tight_layout()
    plt.savefig('visuals/routes_walk_link_count_pdf.png', bbox_inches='tight', dpi=300)
    fig.clf()

    print('Plotting walking route link count cdf.')

    fig = plt.figure()
    ax = plt.subplot(111)
    sns.histplot(data=df1, x='count', ax=ax, stat='count', kde=True, cumulative=True)
    ax.set_xlabel('links')
    ax.set_ylabel('cummulative routes')
    ax.set_title('walking route link count')
    plt.tight_layout()
    plt.savefig('visuals/routes_walk_link_count_cdf.png', bbox_inches='tight', dpi=300)
    fig.clf()

    print('Plotting walking route distance count pdf.')

    df1 = df.query('length <= 6.0')

    fig = plt.figure()
    ax = plt.subplot(111)
    sns.histplot(data=df1, x='length', ax=ax, stat='count', kde=True)
    ax.set_xlabel('route distance (mi)')
    ax.set_ylabel('routes')
    ax.set_title('walking route distance')
    plt.tight_layout()
    plt.savefig('visuals/routes_walk_total_distance_pdf.png', bbox_inches='tight', dpi=300)
    fig.clf()

    print('Plotting walking route distance count cdf.')

    fig = plt.figure()
    ax = plt.subplot(111)
    sns.histplot(data=df1, x='length', ax=ax, stat='count', kde=True, cumulative=True)
    ax.set_xlabel('route distance (mi)')
    ax.set_ylabel('cummulative routes')
    ax.set_title('walking route distance')
    plt.tight_layout()
    plt.savefig('visuals/routes_walk_total_distance_cdf.png', bbox_inches='tight', dpi=300)
    fig.clf()

    print('Fetching biking routes.')

    df = get_route_length(database, 'bike')

    print('Plotting biking route link count pdf.')

    df1 = df.query('count <= 200')

    fig = plt.figure()
    ax = plt.subplot(111)
    sns.histplot(data=df1, x='count', ax=ax, stat='count', kde=True)
    ax.set_xlabel('links')
    ax.set_ylabel('routes')
    ax.set_title('biking route link count')
    plt.tight_layout()
    plt.savefig('visuals/routes_bike_link_count_pdf.png', bbox_inches='tight', dpi=300)
    fig.clf()

    print('Plotting biking route link count cdf.')

    fig = plt.figure()
    ax = plt.subplot(111)
    sns.histplot(data=df1, x='count', ax=ax, stat='count', kde=True, cumulative=True)
    ax.set_xlabel('links')
    ax.set_ylabel('cumulative routes')
    ax.set_title('biking route link count')
    plt.tight_layout()
    plt.savefig('visuals/routes_bike_link_count_cdf.png', bbox_inches='tight', dpi=300)
    fig.clf()

    print('Plotting biking route distance count pdf.')

    df1 = df.query('length <= 10.0')

    fig = plt.figure()
    ax = plt.subplot(111)
    sns.histplot(data=df1, x='length', ax=ax, stat='count', kde=True)
    ax.set_xlabel('route distance (mi)')
    ax.set_ylabel('routes')
    ax.set_title('biking route distance')
    plt.tight_layout()
    plt.savefig('visuals/routes_bike_total_distance_pdf.png', bbox_inches='tight', dpi=300)
    fig.clf()

    print('Plotting biking route link count cdf.')

    fig = plt.figure()
    ax = plt.subplot(111)
    sns.histplot(data=df1, x='length', ax=ax, stat='count', kde=True, cumulative=True)
    ax.set_xlabel('route distance (mi)')
    ax.set_ylabel('cumulative routes')
    ax.set_title('biking route distance')
    plt.tight_layout()
    plt.savefig('visuals/routes_bike_total_distance_cdf.png', bbox_inches='tight', dpi=300)
    fig.clf()


def plot_route_teleportation(database: Database):
    print('Fetching walking routes.')

    df = get_route_teleportation(database, 'walk')

    dist = np.array(df['distance'])
    dist.sort()

    print(np.sum(dist))
    print(np.mean(dist))
    print(np.median(dist))
    print(np.std(dist))
    print(np.size(dist))
    print(np.min(dist))
    print(np.max(dist))
    print(dist[int(np.size(dist) * 0.99)])
    print(dist[int(np.size(dist) * 0.95)])
    print(dist[int(np.size(dist) * 0.90)])

    print('Plotting walking route teleportation distance pdf.')

    df1 = df.query('distance <= 1000.0')

    fig = plt.figure()
    ax = plt.subplot(111)
    sns.histplot(data=df1, x='distance', ax=ax, stat='count', kde=True)
    ax.set_xlabel('teleportation (ft)')
    ax.set_ylabel('routes')
    ax.set_title('route to parcel teleportation')
    plt.tight_layout()
    plt.savefig('visuals/routes_walk_teleportation_pdf.png', bbox_inches='tight', dpi=300)
    fig.clf()

    print('Plotting walking route teleportation distance cdf.')

    fig = plt.figure()
    ax = plt.subplot(111)
    sns.histplot(data=df1, x='distance', ax=ax, stat='count', kde=True, cumulative=True)
    ax.set_xlabel('teleportation (ft)')
    ax.set_ylabel('routes')
    ax.set_title('route to parcel teleportation')
    plt.tight_layout()
    plt.savefig('visuals/routes_walk_teleportation_cdf.png', bbox_inches='tight', dpi=300)
    fig.clf()


def plot_route_time_activity(database: Database):
    print('Fetching route data.')
    routes = get_route_time_activity(database).query('hour <= 25')

    print('Processing route data.')
    group = ['hour', 'mode']
    duration = routes.groupby(group).sum()
    frequency = routes.groupby(group).count()
    mean = routes.groupby(group).mean()
    median = routes.groupby(group).median()

    print('Plotting route data.')

    fig = plt.figure()
    ax = plt.subplot(111)
    sns.lineplot(data=duration, ax=ax, x='hour', y='duration', hue='mode')
    ax.set_xlabel('hour')
    ax.set_ylabel('total routed time (sec)')
    ax.set_title('routed time per hour of day')
    plt.tight_layout()
    plt.savefig('visuals/routes_hour_total_time_line.png', bbox_inches='tight', dpi=300)
    fig.clf()

    fig = plt.figure()
    ax = plt.subplot(111)
    sns.lineplot(data=frequency, ax=ax, x='hour', y='duration', hue='mode')
    ax.set_xlabel('hour')
    ax.set_ylabel('total routed routes')
    ax.set_title('routed routes per hour of day')
    plt.tight_layout()
    plt.savefig('visuals/routes_hour_count_line.png', bbox_inches='tight', dpi=300)
    fig.clf()

    fig = plt.figure()
    ax = plt.subplot(111)
    sns.lineplot(data=mean, ax=ax, x='hour', y='duration', hue='mode')
    ax.set_xlabel('hour')
    ax.set_ylabel('mean route duration (sec)')
    ax.set_title('mean route duration per hour of day')
    plt.tight_layout()
    plt.savefig('visuals/routes_hour_mean_time_line.png', bbox_inches='tight', dpi=300)
    fig.clf()

    fig = plt.figure()
    ax = plt.subplot(111)
    sns.lineplot(data=median, ax=ax, x='hour', y='duration', hue='mode')
    ax.set_xlabel('hour')
    ax.set_ylabel('median route duration (sec)')
    ax.set_title('median route duration per hour of day')
    plt.tight_layout()
    plt.savefig('visuals/routes_hour_median_time_line.png', bbox_inches='tight', dpi=300)
    fig.clf()



def main():
    db_path = 'database.db'
    database = Database(db_path, readonly=True)

    # plot_route_lengths(database)
    # plot_route_teleportation(database)
    plot_route_time_activity(database)


if __name__ == '__main__':
    main()
    