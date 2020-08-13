
import os
import random
import logging as log


from argparse import ArgumentParser, SUPPRESS
from typing import Callable, Iterator, List, IO

from icarus.util.iter import pair
from icarus.util.file import multiopen
from icarus.util.sqlite import SqliteUtil


def hhmmss(secs):
    hours = secs // 3600
    secs -= hours * 3600
    mins = secs // 60
    secs -= mins * 60
    return ':'.join(str(t).zfill(2) for t in (hours, mins, secs))


def xy(point):
    return point[7:-1].split(' ')


def fetch_activities(database: SqliteUtil, min_agent: int, max_agent: int):
    query = f'''
        SELECT
            activities.agent_id,
            activities.agent_idx,
            activities.type,
            activities.start,
            activities.end,
            parcels.center
        FROM activities
        INNER JOIN parcels
        ON activities.apn = parcels.apn
        INNER JOIN temp.sample
        USING(agent_id)
        WHERE activities.agent_id >= {min_agent}
        AND activities.agent_id < {max_agent}
        ORDER BY agent_id, agent_idx;
    '''
    database.cursor.execute(query)
    result = database.cursor.fetchall()

    return result


def fetch_legs(database: SqliteUtil, min_agent: int, max_agent: int):
    query = f'''
        SELECT
            legs.agent_id,
            legs.agent_idx,
            legs.mode,
            legs.start,
            legs.end,
            legs.duration
        FROM legs
        INNER JOIN temp.sample
        USING(agent_id)
        WHERE legs.agent_id >= {min_agent}
        AND legs.agent_id < {max_agent}
        ORDER BY agent_id, agent_idx;
    '''
    database.cursor.execute(query)
    result = database.cursor.fetchall()

    return result


def get_max(database: SqliteUtil, table: str, col: str):
    query = f'''
        SELECT max({col})
        FROM {table};
    '''
    database.cursor.execute(query)
    result = database.cursor.fetchall()

    return result[0][0]


def write_plans(plans: IO, activities: Iterator, 
        legs: Iterator, virtual: List[str]):
    per_frmt = '<person id="%s"><plan selected="yes">'
    str_frmt = '<act end_time="%s" type="%s" x="%s" y="%s"/>'
    reg_frmt = '<act start_time="%s" end_time="%s" type="%s" x="%s" y="%s"/>'
    end_frmt = '<act start_time="%s" type="%s" x="%s" y="%s"/>'
    leg_frmt = '<leg trav_time="%s" mode="%s"/>'

    modes = {
        'car': 'car',
        'walk': 'netwalk',
        'pt': 'pt',
        'bike': 'bike'
    }
    
    act = next(activities)
    agent = act[0]
    x, y = xy(act[5])
    plans.write(per_frmt % (agent,))
    plans.write(str_frmt % (act[4], act[2], x, y))
    act = next(activities)

    for leg in legs:
        x, y = xy(act[5])
        mode = modes[leg[2]]
        if mode in virtual:
            plans.write(leg_frmt % (0.0, 'fakemode'))
            plans.write(reg_frmt % (leg[3], leg[4], 'fakeactivity', x, y))
            plans.write(leg_frmt % (0.0, f'fake{mode}'))
        else:
            plans.write(leg_frmt % (leg[5], mode))

        peek = next(activities, None)
        if peek is None:
            plans.write(end_frmt % (act[3], act[2], x, y))
            plans.write('</plan></person>')
        elif peek[1] == 0:
            agent = peek[0]
            plans.write(end_frmt % (act[3], act[2], x, y))
            plans.write('</plan></person>')
            plans.write(per_frmt % (agent,))
            plans.write(str_frmt % (peek[4], peek[2], x, y))
            act = next(activities)
        else:
            plans.write(reg_frmt % (act[3], act[4], act[2], x, y))
            act = peek


def generate_sample(database: SqliteUtil, maxsize: int = None, 
        perc: float = None):
    agents = database.count_rows('agents')
    if perc is not None:
        agents = int(perc * agents)
    if maxsize is not None:
        agents = min(agents, maxsize)
    
    query = f'''
        CREATE TEMPORARY TABLE sample
        AS SELECT *
        FROM agents
        ORDER BY RAND()
        LIMIT {agents};
    '''
    database.cursor.execute(query)

    query = '''
        CREATE INDEX temp.sample 
        ON sample(agnet_id);
    '''

    database.connection.commit()



def generate_plans(database: SqliteUtil, path: Callable[[str],str],
        virtual: List[str], maxsize: int = None, perc: float = None):
    log.info('Generating sample population.')
    generate_sample(database, maxsize, perc)

    log.info('Starting plans generation.')
    binsize = 100000
    max_agent = get_max(database, 'agents', 'agent_id') + 1
    bins = pair(range(0, max_agent + binsize, binsize))
    
    savepath = path('input/plans.xml.gz')
    with multiopen(savepath, 'wt') as plans:
        plans.write(
            '<?xml version="1.0" encoding="utf-8"?>'
            '<!DOCTYPE plans SYSTEM "http://www.matsim.org/files/dtd/plans_v4.dtd">'
            '<plans>'
        )
        for low, high in bins:
            log.info(f'Writing plans {low} to {high}.')
            activities = fetch_activities(database, low, high)
            legs = fetch_legs(database, low, high)
            write_plans(plans, iter(activities), iter(legs), virtual)
        plans.write('</plans>')


    savepath = path('input/vehicles.xml.gz')
    with multiopen(savepath, 'wt') as vehicles:
        vehicles.write('''<?xml version="1.0" encoding="UTF-8" ?>
            <vehicleDefinitions
                xmlns="http://www.matsim.org/files/dtd"
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                xsi:schemaLocation="http://www.matsim.org/files/dtd 
                    http://www.matsim.org/files/dtd/vehicleDefinitions_v2.0.xsd">''')

        vehicles.write('''
            <vehicleType id="Bus">
                <attributes>
                    <attribute name="accessTimeInSecondsPerPerson" class="java.lang.Double">0.5</attribute>
                    <attribute name="doorOperationMode" class="java.lang.String">serial</attribute>
                    <attribute name="egressTimeInSecondsPerPerson" class="java.lang.Double">0.5</attribute>
                </attributes>
                <capacity seats="70" standingRoomInPersons="0"/>
                <length meter="18.0"/>
                <width meter="2.5"/>
                <passengerCarEquivalents pce="2.8"/>
                <networkMode networkMode="Bus"/>
                <flowEfficiencyFactor factor="1.0"/>
            </vehicleType>''')

        vehicles.write('''
            <vehicleType id="Tram">
                <attributes>
                    <attribute name="accessTimeInSecondsPerPerson" class="java.lang.Double">0.25</attribute>
                    <attribute name="doorOperationMode" class="java.lang.String">serial</attribute>
                    <attribute name="egressTimeInSecondsPerPerson" class="java.lang.Double">0.25</attribute>
                </attributes>
                <capacity seats="180" standingRoomInPersons="0"/>
                <length meter="36.0"/>
                <width meter="2.4"/>
                <passengerCarEquivalents pce="5.2"/>
                <networkMode networkMode="Tram"/>
                <flowEfficiencyFactor factor="1.0"/>
            </vehicleType>''')

        vehicles.write('''
            <vehicleType id="car">
                <attributes>
                    <attribute name="accessTimeInSecondsPerPerson" class="java.lang.Double">1.0</attribute>
                    <attribute name="doorOperationMode" class="java.lang.String">serial</attribute>
                    <attribute name="egressTimeInSecondsPerPerson" class="java.lang.Double">1.0</attribute>
                </attributes>
                <capacity seats="5" standingRoomInPersons="0"/>
                <length meter="7.5"/>
                <width meter="1.0"/>
                <maximumVelocity meterPerSecond="40.0"/>
                <passengerCarEquivalents pce="1.0"/>
                <networkMode networkMode="car"/>
                <flowEfficiencyFactor factor="1.0"/>
            </vehicleType>''')

        vehicles.write('''
            <vehicleType id="bike">
                <attributes>
                    <attribute name="accessTimeInSecondsPerPerson" class="java.lang.Double">1.0</attribute>
                    <attribute name="doorOperationMode" class="java.lang.String">serial</attribute>
                    <attribute name="egressTimeInSecondsPerPerson" class="java.lang.Double">1.0</attribute>
                </attributes>
                <capacity seats="1" standingRoomInPersons="0"/>
                <length meter="5.0"/>
                <width meter="1.0"/>
                <maximumVelocity meterPerSecond="4.4704"/>
                <passengerCarEquivalents pce="0.25"/>
                <networkMode networkMode="bike"/>
                <flowEfficiencyFactor factor="1.0"/>
            </vehicleType>''')

        vehicles.write('''
            <vehicleType id="netwalk">
                <attributes>
                    <attribute name="accessTimeInSecondsPerPerson" class="java.lang.Double">1.0</attribute>
                    <attribute name="doorOperationMode" class="java.lang.String">serial</attribute>
                    <attribute name="egressTimeInSecondsPerPerson" class="java.lang.Double">1.0</attribute>
                </attributes>
                <capacity seats="1" standingRoomInPersons="0"/>
                <length meter="1.0"/>
                <width meter="1.0"/>
                <maximumVelocity meterPerSecond="1.4"/>
                <passengerCarEquivalents pce="0.0"/>
                <networkMode networkMode="netwalk"/>
                <flowEfficiencyFactor factor="1.0"/>
            </vehicleType>''')

        vehicles.write('</vehicleDefinitions>')


def main():
    desc = (
        ''
    )
    parser = ArgumentParser('icarus.generate.plans', description=desc, add_help=False)

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

    configuration = parser.add_argument_group('configuration options')
    configuration.add_argument('--perc', type=float, dest='perc', default=1.0,
        help='proportion of agents to use in the population')
    configuration.add_argument('--max', type=int, dest='max', default=None,
        help='maximum number of agents to use in population')
    configuration.add_argument('--seed', type=int, dest='seed', default=None,
        help='number to seed randomness of population generation')

    args = parser.parse_args()

    path = lambda x: os.path.abspath(os.path.join(args.dir, x))
    os.makedirs(path('logs'), exist_ok=True)
    homepath = path('')
    logpath = path('logs/generate_plans.log')
    dbpath = path('database.db')

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

    log.info('Running plans generating module.')
    log.info(f'Loading data from {homepath}.')
    log.info('Verifying process metadata/conditions.')

    if args.seed is not None:
        random.seed(args.seed)

    database = SqliteUtil(dbpath)
    database.connection.create_function('RAND', 0, random.random)

    virtual = ['pt', 'car']

    generate_plans(database, path, virtual, args.max, args.perc)


if __name__ == '__main__':
    main()

