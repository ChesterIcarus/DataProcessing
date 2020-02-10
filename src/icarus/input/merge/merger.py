
import gzip
import logging as log

from xml.etree.ElementTree import tostring, iterparse
from collections import defaultdict, deque

from icarus.input.merge.database import PlansMergerDatabase
from icarus.util.filesys import FilesysUtil
from icarus.util.config import ConfigUtil


class XmlIterator:
    def __init__(self, filepath):
        self.filepath = filepath

    def __iter__(self):
        self.parser = iterparse(self.filepath, events=('start', 'end'))
        _, self.root = next(self.parser)
        self.path = deque([self.root.tag])
        return self

    def __next__(self):
        evt, elem = next(self.parser)
        if evt == 'start':
            self.path.append(elem.tag)
        elif evt == 'end':
            tag = self.path.pop()
            if tag != elem.tag:
                raise RuntimeError('Tag mismatch in XML iteration.')
        return evt, elem

    def skip(self):
        size = len(self.path)
        tag = self.path[-1]
        evt, elem = next(self)
        while len(self.path) >= size:
            evt, elem = next(self)
        if tag != elem.tag or evt != 'end':
            raise RuntimeError('Tag mismatch in XML element skipping.')
        return elem


class PlansMerger:
    def __init__(self, database):
        self.database = PlansMergerDatabase(database)


    @staticmethod
    def time(secs):
        hours = secs // 3600
        secs -= hours * 3600
        mins = secs // 60
        secs -= mins * 60
        return ':'.join(str(t).zfill(2) for t in (hours, mins, secs))

    
    @classmethod
    def validate_config(self, configpath, specspath=None):
        config = ConfigUtil.load_config(configpath)
        # specs = ConfigUtil.load_specs(specspath)
        # config = ConfigUtil.verify_config(specs, config)

        return config


    def get_vehicles(self, agents):
        route_list = self.database.get_routes(agents)
        act_list = self.database.get_activities(agents)

        routes = defaultdict(list)
        acts = defaultdict(list)
        cars = set()

        for route in route_list:
            if route[2] == 11:
                cars.add((route[5], 'netwalk'))
            elif route[2] == 12:
                cars.add((route[5], 'bike'))
            elif route[2] in (1,2,3,4,13,14):
                cars.add((route[5], 'car'))
            else: 
                continue
            routes[route[0]].append(route)

        for act in act_list:
            acts[act[0]].append(act)

        return routes, acts, cars


    def run(self, config):
        planspath = config['planspath']
        mergepath = config['outfile']
        vehcpath = config['vehiclesfile']

        log.info(f'Loading plans from {planspath}.')
        if planspath.split('.')[-1] == 'gz':
            plansfile = gzip.open(planspath, mode='rb')
        else:
            plansfile = open(planspath, mode='rb')
        parser = iterparse(plansfile, events=('start', 'end'))
        parser = iter(parser)
        evt, root = next(parser)

        agent = None
        agents = set()
        count = 0

        log.info('Iterating over plans to identify agents.')
        for evt, elem in parser:
            if evt == 'start':
                if elem.tag == 'person':
                    agent = int(elem.get('id'))
                    agents.add(agent)
                    count += 1
                    if count % 10000 == 0:
                        root.clear()
        root.clear()
        plansfile.close()
        del parser
        del plansfile

        log.info(f'Found {len(agents)} agents in plans.')
        log.info(f'Fetching vehicular data for agent plans.')
        legs, acts, cars = self.get_vehicles(agents)

        log.info(f'Creating merged plans file at {mergepath}.')
        if planspath.split('.')[-1] == 'gz':
            plansfile = gzip.open(planspath, mode='rb')
        else:
            plansfile = open(planspath, mode='rb')
        if mergepath.split('.')[-1] == 'gz':
            mergefile = gzip.open(mergepath, mode='wt')
        else:
            mergefile = open(mergepath, mode='wt')

        mergefile.write('<?xml version="1.0" encoding="utf-8"?><!DOCTYPE population '
            'SYSTEM "http://www.matsim.org/files/dtd/population_v6.dtd"><population>')

        agent = None
        xmliter = XmlIterator(plansfile)        
        act = []
        leg = []
        count = 0
        n = 1

        activities = ('home', 'workplace', 'university', 'school', 'shopping',
            'other_maintenence', 'eating', 'breakfast', 'lunch', 'dinner',
            'visiting', 'other_discretionary', 'special_event', 'work',
            'work_business', 'work_lunch', 'work_other', 'work_related', 'asu_related')
        modes = ('car', 'bike', 'netwalk')

        person_frmt = '<person id="%s">'
        plan_frmt = '<plan score="%s" selected="%s">'
        start_frmt = '<activity end_time="%s" type="%s" x="%s" y="%s"/>'
        act_frmt = '<activity start_time="%s" end_time="%s" type="%s" x="%s" y="%s"/>'
        end_frmt = '<activity start_time="%s" type="%s" x="%s" y="%s"/>'
        leg_frmt = '<leg dep_time="%s" mode="%s" trav_time="%s">'
        route_frmt = ('<route distance="%s" end_link="%s" start_link="%s" '
            'trav_time="%s" type="%s" vehicleRefId="%s">%s</route>')

        log.info('Iterating over plans and generating merged plans file.')
        for evt, elem in xmliter:
            if evt == 'start':
                if elem.tag == 'person':
                    agent = int(elem.get('id'))
                    mergefile.write(person_frmt % agent)
                    count += 1
                    if count % 10000 == 0:
                        mergefile.flush()
                        xmliter.root.clear()
                    if n == count:
                        log.info(f'Writing plan {count}.')
                        n <<= 1
                elif elem.tag == 'plan':
                    selected = elem.get('selected', 'no')
                    score = elem.get('score')
                    if selected == 'yes':
                        mergefile.write(plan_frmt % (score, selected))
                    else:
                        elem = xmliter.skip()
                        mergefile.write(tostring(elem).decode('utf-8'))
                elif elem.tag == 'activity':
                    if elem.get('type') in activities:
                        act = acts[agent].pop(0)
                        kind = elem.get('type')
                        x = elem.get('x')
                        y = elem.get('y')
                        start = self.time(act[2])
                        end = self.time(act[3])
                        if elem.get('start_time') is None:
                            mergefile.write(start_frmt % (end, kind, x, y))
                        elif elem.get('end_time') is None:
                            mergefile.write(end_frmt % (start, kind, x, y))
                        else:
                            mergefile.write(act_frmt % (start, end, kind, x, y))
                        xmliter.skip()
                    else:
                        elem = xmliter.skip()
                        mergefile.write(tostring(elem).decode('utf-8'))
                elif elem.tag == 'leg':
                    if elem.get('mode') in modes:
                        leg = legs[agent].pop(0)
                        mergefile.write(leg_frmt % (
                            self.time(leg[3]), 
                            elem.get('mode'), 
                            self.time(leg[4])))
                    else:
                        elem = xmliter.skip()
                        mergefile.write(tostring(elem).decode('utf-8'))
                elif elem.tag == 'route':
                    pass
                elif elem.tag == 'attributes':
                    elem = xmliter.skip()
                    mergefile.write(tostring(elem).decode('utf-8'))
                else:
                    path = '.'.join(list(xmliter.path))
                    log.error(f'Found expected tag "{elem.tag}" at "{path}".')
                    raise RuntimeError

            elif evt == 'end':
                if elem.tag == 'route':
                    mergefile.write(route_frmt % (
                        elem.get('distance'),
                        elem.get('end_link'),
                        elem.get('start_link'),
                        self.time(leg[4]),
                        elem.get('type'),
                        leg[5],
                        elem.text if elem.text is not None else ''))
                else:
                    mergefile.write('</%s>' % elem.tag)

        if count != (n >> 1):
            log.info(f'Writing plan {count}.')
                
        mergefile.close()
        del xmliter

        log.info(f'Creating vehicles file at {vehcpath}.')
        if vehcpath.split('.')[-1] == 'gz':
            vehiclesfile = gzip.open(vehcpath, mode='wt')
        else:
            vehiclesfile = open(vehcpath, mode='wt')
        
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

        vehc_formt = '<vehicle id="%s" type="%s"/>'
        count = 0
        n = 1

        log.info('Iterating over vehicles and writing vehicle definitions.')
        for car in cars:
            vehiclesfile.write(vehc_formt % car)
            count += 1
            if count % 10000 == 0:
                vehiclesfile.flush()
            if count == n:
                log.info(f'Writing vehicle {n}.')
                n <<= 1

        if count != (n >> 1):
            log.info(f'Writing vehicle {n}.')

        vehiclesfile.write('</vehicleDefinitions>')
        vehiclesfile.close()
