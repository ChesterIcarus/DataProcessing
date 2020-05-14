
import math
import logging as log

from icarus.util.file import multiopen, exists, touch
from icarus.util.sqlite import SqliteUtil
from icarus.util.general import counter 


def hhmmss(secs):
    hours = secs // 3600
    secs -= hours * 3600
    mins = secs // 60
    secs -= mins * 60
    return ':'.join(str(t).zfill(2) for t in (hours, mins, secs))


def xy(point):
    return point[7:-1].split(' ')


class Leg:
    __slots__ = ('agent_id', 'agent_idx', 'mode', 'duration')

    def __init__(self, leg):
        self.agent_id, self.agent_idx, self.mode, self.duration = leg

    def virtualize(self, activity):
        string = Leg([None, None, 'fakemode', 0]).encode()
        string += Activity([None, None, activity.start - self.duration, 
            activity.start, 'fakeactivity', activity.x, activity.y]).encode()
        string += Leg([None, None, self.mode, self.duration]).encode()
        return string

    def encode(self, activity=None):
        string = None
        if self.mode in ('car', 'pt') and activity is not None:
            string = self.virtualize(activity)
        else:
            if self.mode == 'walk':
                self.mode = 'netwalk'
            dur = hhmmss(self.duration)
            mode = self.mode
            string = f'<leg trav_time="{dur}" mode="{mode}"/>'
        return string



class Activity:
    __slots__ = ('agent_id', 'agent_idx', 'start', 'end', 'type', 'x', 'y')

    def __init__(self, activity):
        self.agent_id, self.agent_idx, self.start, self.end, \
            self.type, self.x, self.y = activity

    def encode_start(self):
        string = '<act end_time="%s" type="%s" x="%s" y="%s"/>'
        return string % (hhmmss(self.end), self.type, self.x, self.y)

    def encode(self):
        string = '<act start_time="%s" end_time="%s" type="%s" x="%s" y="%s"/>'
        return string % (hhmmss(self.start), hhmmss(self.end), self.type, self.x, self.y)

    def encode_end(self):
        string = '<act start_time="%s" type="%s" x="%s" y="%s"/>'
        return string % (hhmmss(self.start), self.type, self.x, self.y)
    



class Plans:
    def __init__(self, database: SqliteUtil):
        self.database = database


    def create_sample(self, size, transit=None, vehicle=None, 
            walk=None, bike=None, party=None):
        conditions = []
        condition = ''
        if transit is not None:
            conditions.append(f'uses_transit = {int(transit)}')
        if vehicle is not None:
            conditions.append(f'uses_vehicle = {int(vehicle)}')
        if walk is not None:
            conditions.append(f'uses_walk = {int(walk)}')
        if bike is not None:
            conditions.append(f'uses_bike = {int(bike)}')
        if party is not None:
            conditions.append(f'uses_party = {int(party)}')
        if len(conditions):
            condition = 'WHERE ' + ' AND '.join(conditions)

        self.database.drop_table('sample')
        self.database.cursor.execute(f'''
            CREATE TABLE sample AS
            SELECT *
            FROM agents
            {condition}
            ORDER BY RANDOM()
            LIMIT {size};   ''')
        self.database.cursor.execute(
            'CREATE UNIQUE INDEX sample_agent ON sample(agent_id)')
        self.database.connection.commit()


    def delete_sample(self):
        self.database.drop_table('sample')
        self.database.connection.commit()

    
    def fetch_agents(self, table):
        self.database.cursor.execute(f'''
            SELECT 
                agent_id,
                plan_size
            FROM {table}
            ORDER BY agent_id;  ''')
        return self.database.cursor.fetchall()

    
    def fetch_activities(self, table):
        self.database.cursor.execute(f'''
            SELECT
                activities.agent_id,
                activities.agent_idx,
                activities.start,
                activities.end,
                activities.type,
                parcels.centroid
            FROM activities
            INNER JOIN parcels
            USING(apn)
            INNER JOIN {table}
            USING(agent_id)
            ORDER BY
                agent_id,
                agent_idx;  ''')
        for activity in self.database.cursor.fetchall():
            yield Activity(list(activity[:-1]) + list(xy(activity[-1])))

    
    def fetch_legs(self, table):
        self.database.cursor.execute(f'''
            SELECT
                agent_id,
                agent_idx,
                mode,
                duration
            FROM legs
            INNER JOIN {table}
            USING(agent_id);    ''')
        for leg in self.database.cursor.fetchall():
            yield Leg(leg)


    def ready(self):
        tables = ('activities', 'legs', 'agents')
        present = self.database.table_exists(*tables)
        if len(present) < len(tables):
            missing = ', '.join(set(tables) - set(present))
            log.info(f'Could not find tables {missing} in database.')
        return len(present) == len(tables)


    def complete(self, planspath, vehiclespath):
        complete = False
        if exists(planspath):
            complete = True
            log.info(f'Found file {planspath} already generated.')
        if exists(vehiclespath):
            complete = True
            log.info(f'Found file {vehiclespath} already generated.')
        return complete
        

    def generate(self, planspath, vehiclespath, modes, sample_percent=1, 
            sample_size=math.inf, transit=None, vehicle=None, walk=None, 
            bike=None, party=None):
        log.info('Creating a sample population.')
        conditions = {
            'transit': transit, 
            'vehicle': vehicle, 
            'walk': walk, 
            'bike': bike, 
            'party': party
        }
        max_size = self.database.count_rows('agents')
        size = min(max_size * sample_percent, sample_size)

        table = 'agents'
        if size < max_size or any(cond is not None for cond in conditions.values()):
            table = 'sample'
            self.create_sample(size, **conditions)
            actual = self.database.count_rows('sample')
            if actual < size:
                log.info(f'Target sample was {size} but only found {actual} '
                    'agents under specified parameters.')

        log.info('Fetching agents, activities and legs.')
        agents = self.fetch_agents(table)
        activities = self.fetch_activities(table)
        legs = self.fetch_legs(table)

        log.info('Iterating over plans and generating plans file.')
        touch(planspath)
        plansfile = multiopen(planspath, mode='wt')
        plansfile.write('<?xml version="1.0" encoding="utf-8"?><!DOCTYPE plans'
            ' SYSTEM "http://www.matsim.org/files/dtd/plans_v4.dtd"><plans>')

        for agent_id, plan_size in counter(agents, 'Writing plan %s.'):
            plansfile.write(f'<person id="{agent_id}"><plan selected="yes">')
            plansfile.write(next(activities).encode_start())
            for _ in range(plan_size // 2 - 1):
                leg = next(legs)
                activity = next(activities)
                plansfile.write(leg.encode(activity))
                plansfile.write(activity.encode())
            leg = next(legs)
            activity = next(activities)
            plansfile.write(leg.encode(activity))
            plansfile.write(activity.encode_end())
            plansfile.write('</plan></person>')
            plansfile.flush()

        plansfile.write('</plans>')

        log.info('Writing vehicle definitions file.')
        touch(vehiclespath)
        vehiclesfile = multiopen(vehiclespath, mode='wt')

        vehiclesfile.write('''<?xml version="1.0" encoding="UTF-8" ?>
            <vehicleDefinitions
                xmlns="http://www.matsim.org/files/dtd"
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                xsi:schemaLocation="http://www.matsim.org/files/dtd 
                    http://www.matsim.org/files/dtd/vehicleDefinitions_v2.0.xsd">''')

        vehiclesfile.write('''
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

        vehiclesfile.write('''
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

        vehiclesfile.write('''
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

        vehiclesfile.write('''
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

        vehiclesfile.write('''
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

        vehiclesfile.write('</vehicleDefinitions>')
        vehiclesfile.close()

        log.info('Cleaning up.')
        self.delete_sample()


        



