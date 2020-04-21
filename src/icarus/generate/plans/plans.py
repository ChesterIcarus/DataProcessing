
import math
import logging as log
from icarus.util.file import multiopen
from icarus.util.general import chunk, defaultdict, bins
from shapely.wkt import loads


class Sampling:
    @staticmethod
    def time(secs):
        hours = secs // 3600
        secs -= hours * 3600
        mins = secs // 60
        secs -= mins * 60
        return ':'.join(str(t).zfill(2) for t in (hours, mins, secs))

    
    @staticmethod
    def xy(point):
        return point[7:-1].split(' ')


    @staticmethod
    def encode_agent(agent):
        string = '<person id="%s"><plan selected="yes">'
        return string % agent[0]


    @staticmethod
    def encode_start_activity(activity):
        string = '<act end_time="%s" type="%s" x="%s" y="%s"/>'
        return string % (
            Sampling.time(activity[3]),
            activity[4],
            *Sampling.xy(activity[5]))

    
    @staticmethod
    def encode_activity(activity):
        string = '<act start_time="%s" end_time="%s" type="%s" x="%s" y="%s"/>'
        return string % (
            Sampling.time(activity[2]),
            Sampling.time(activity[3]),
            activity[4],
            *Sampling.xy(activity[5]))
    

    @staticmethod
    def encode_end_activity(activity):
        string = '<act start_time="%s" type="%s" x="%s" y="%s"/>'
        return string % (
            Sampling.time(activity[3]),
            activity[4],
            *Sampling.xy(activity[5]))


    @staticmethod
    def encode_leg(leg):
        string = '<leg trav_time="%s" mode="%s"/>'
        return string % (
            Sampling.time(leg[3]),
            leg[2])

    
    @staticmethod
    def virtualize(leg, activity):
        fakeleg = Sampling.encode_leg([
            None, 
            None, 
            'fakemode', 
            0])
        fakeactivity = Sampling.encode_activity([
            None,
            None,
            activity[2] - leg[3],
            activity[2],
            'fakeactivity',
            activity[5]])
        realleg = Sampling.encode_leg([
            None,
            None,
            leg[2],
            0])
        return fakeleg + fakeactivity + realleg


    def __init__(self, database):
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

    
    def fetch_agents(self):
        self.database.cursor.execute(f'''
            SELECT 
                agent_id,
                plan_size
            FROM sample
            ORDER BY agent_id;  ''')
        return self.database.cursor.fetchall()

    
    def fetch_activities(self):
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
            INNER JOIN sample
            USING(agent_id)
            ORDER BY
                agent_id,
                agent_idx;  ''')
        return self.database.cursor.fetchall()

    
    def fetch_legs(self):
        self.database.cursor.execute(f'''
            SELECT
                agent_id,
                agent_idx,
                mode,
                duration
            FROM legs
            INNER JOIN sample
            USING(agent_id);    ''')
        return self.database.cursor.fetchall()


    def complete(self, config):
        return False
        

    def sample(self, planspath, vehiclespath, sample_perc=1, sample_size=math.inf,
            virtual=[], transit=None, vehicle=None, walk=None, bike=None, party=None):
        log.info('Creating a sample population.')
        population = self.database.count_rows('agents')
        size = population * sample_perc
        if size is not None:
            size = min(size, sample_size)
        self.create_sample(sample_size, transit, vehicle, walk, bike, party)

        actual = self.database.count_rows('sample')
        if actual < size:
            log.info(f'Target sample was {size} but only found {actual} '
                'agents under specified parameters.')

        log.info('Fetching agents, activities and legs.')
        agents = self.fetch_agents()
        activities = iter(self.fetch_activities())
        legs = iter(self.fetch_legs())

        log.info('Iterating over plans and generating plans file.')
        count = 0
        n = 1       

        plansfile = multiopen(planspath, mode='wt')
        plansfile.write('<?xml version="1.0" encoding="utf-8"?><!DOCTYPE plans'
            ' SYSTEM "http://www.matsim.org/files/dtd/plans_v4.dtd"><plans>')

        for agent in agents:
            plansfile.write(Sampling.encode_agent(agent))
            plansfile.write(Sampling.encode_start_activity(next(activities)))
            for _ in range(agent[1] // 2 - 1):
                leg = next(legs)
                activity = next(activities)
                if leg[2] in virtual:
                    plansfile.write(Sampling.virtualize(leg, activity))
                else:
                    plansfile.write(Sampling.encode_leg(leg))
                plansfile.write(Sampling.encode_activity(activity))
            leg = next(legs)
            activity = next(activities)
            if leg[2] in virtual:
                plansfile.write(Sampling.virtualize(leg,activity))
            else:
                plansfile.write(Sampling.encode_leg(leg))
            plansfile.write(Sampling.encode_end_activity(activity))
            plansfile.write('</plan></person>')

            count += 1
            if count == n:
                log.info(f'Writing plan {count}.')
                n <<= 1

        if count != (n >> 1):
            log.info(f'Writing plan {count}.')

        plansfile.write('</plans>')
        plansfile.close()

        try:
            next(activities)
            raise RuntimeError('Agent plan sizes did not align with activity count.')
        except StopIteration:
            log.info('Confirmed all activities used.')

        try:
            next(legs)
            raise RuntimeError('Agent plan sizes did not align with leg count.')
        except StopIteration:
            log.info('Confirmed all legs used.')

        log.info('Writing vehicle definitions file.')
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
                <networkMode networkMode="bike"/>
                <flowEfficiencyFactor factor="1.0"/>
            </vehicleType>''')

        vehiclesfile.write('</vehicleDefinitions>')
        vehiclesfile.close()

        log.info('Cleaning up.')
        self.delete_sample()


        



