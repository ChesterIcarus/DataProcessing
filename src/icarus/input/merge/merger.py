
import logging as log

from xml.etree.ElementTree import tostring, iterparse
from collections import defaultdict, deque

from icarus.input.merge.database import PlansMergerDatabase
from icarus.util.filesys import FilesysUtil


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
            print(self.path)
            print(tag)
            print(elem.tag)
            print(evt)
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


    def get_vehicles(self, agents):
        route_list = self.database.get_routes(agents)
        act_list = self.database.get_activities(agents)

        routes = defaultdict(list)
        acts = defaultdict(list)
        cars = set()

        for route in route_list:
            if route[2] == 11:
                cars.add((route[5], 'walk'))
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

        log.info(f'Loading plans from {planspath}.')
        parser = iterparse(planspath, events=('start', 'end'))
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
        del parser

        log.info(f'Found {len(agents)} agents in plans.')
        log.info(f'Fetching vehicular data for agent plans.')
        legs, acts, cars = self.get_vehicles(agents)

        outfile = open(config['outfile'], 'w')
        outfile.write('<?xml version="1.0" encoding="utf-8"?>'
            '<!DOCTYPE population SYSTEM "http://www.matsim.org/files/dtd/population_'
            'v6.dtd"><population>')

        agent = None
        xmliter = XmlIterator(planspath)
        iter(xmliter)
        act = []
        leg = []
        count = 0
        n = 1

        activities = ('home', 'workplace', 'university', 'school', 'shopping',
            'other_maintenence', 'eating', 'breakfast', 'lunch', 'dinner',
            'visiting', 'other_discretionary', 'special_event', 'work',
            'work_business', 'work_lunch', 'work_other', 'work_related', 
            'asu_related')
        modes = ('car', 'bike', 'walk')

        person_frmt = '<person id="%s">'
        plan_frmt = '<plan score="%s" selected="%s">'
        start_frmt = '<activity end_time="%s" type="%s" x="%s" y="%s"/>'
        act_frmt = '<activity start_time="%s" end_time="%s" type="%s" x="%s" y="%s"/>'
        end_frmt = '<activity start_time="%s" type="%s" x="%s" y="%s"/>'
        leg_frmt = '<leg dep_time="%s" mode="%s" trav_time="%s">'
        route_frmt = ('<route distance="%s" end_link="%s" start_link="%s" '
            'trav_time="%s" type="%s" vehicleRefId="%s">%s</route>')

        log.info('Iterating over plans to append/modify vehicular data.')
        for evt, elem in xmliter:
            if evt == 'start':
                if elem.tag == 'person':
                    agent = int(elem.get('id'))
                    outfile.write(person_frmt % agent)
                    count += 1
                    if count % 10000 == 0:
                        outfile.flush()
                        root.clear()
                    if n == count:
                        log.info(f'Writing plan {count}.')
                        n <<= 1
                elif elem.tag == 'plan':
                    selected = elem.get('selected', 'no')
                    score = elem.get('score')
                    if selected == 'yes':
                        outfile.write(plan_frmt % (score, selected))
                    else:
                        elem = xmliter.skip()
                        outfile.write(tostring(elem).decode('utf-8'))
                elif elem.tag == 'activity':
                    if elem.get('type') in activities:
                        act = acts[agent].pop(0)
                        kind = elem.get('type')
                        x = elem.get('x')
                        y = elem.get('y')
                        start = self.time(act[2])
                        end = self.time(act[3])
                        if elem.get('start_time') is None:
                            outfile.write(start_frmt % (end, kind, x, y))
                        elif elem.get('end_time') is None:
                            outfile.write(end_frmt % (start, kind, x, y))
                        else:
                            outfile.write(act_frmt % (start, end, kind, x, y))
                        xmliter.skip()
                    else:
                        elem = xmliter.skip()
                        outfile.write(tostring(elem).decode('utf-8'))
                elif elem.tag == 'leg':
                    if elem.get('mode') in modes:
                        leg = legs[agent].pop(0)
                        outfile.write(leg_frmt % (
                            self.time(leg[3]), 
                            elem.get('mode'), 
                            self.time(leg[4])))
                    else:
                        elem = xmliter.skip()
                        outfile.write(tostring(elem).decode('utf-8'))
                elif elem.tag == 'route':
                    pass
                elif elem.tag == 'attributes':
                    elem = xmliter.skip()
                    outfile.write(tostring(elem).decode('utf-8'))
                else:
                    path = '.'.join(list(xmliter.path))
                    log.error(f'Found expected tag "{elem.tag}" at "{path}".')
                    raise RuntimeError

            elif evt == 'end':
                if elem.tag == 'route':
                    outfile.write(route_frmt % (
                        elem.get('distance'),
                        elem.get('end_link'),
                        elem.get('start_link'),
                        self.time(leg[4]),
                        elem.get('type'),
                        leg[5],
                        elem.text if elem.text is not None else ''))
                else:
                    outfile.write('</%s>' % elem.tag)
                
        outfile.close()
        del xmliter

        log.info(f'Creating vehicles file at {config["vehiclesfile"]}.')

        vehiclesfile = open(config['vehiclesfile'], 'w')
        
        vehiclesfile.write('<?xml version="1.0" encoding="UTF-8" ?>'
            '<vehicleDefinitions xmlns="http://www.matsim.org/files/dtd" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xsi:schemaLocation="http://www.matsim.org/files/dtd '
            'http://www.matsim.org/files/dtd/vehicleDefinitions_v1.0.xsd">')
        vehiclesfile.write('''
            <vehicleType id="Bus">
                <capacity>
                    <seats persons="70"/>
                    <standingRoom persons="0"/>
                </capacity>
                <length meter="18.0"/>
                <width meter="2.5"/>
                <accessTime secondsPerPerson="0.5"/>
                <egressTime secondsPerPerson="0.5"/>
                <doorOperation mode="serial"/>
                <passengerCarEquivalents pce="2.8"/>
            </vehicleType>''')
        vehiclesfile.write('''
            <vehicleType id="Tram">
                <capacity>
                    <seats persons="180"/>
                    <standingRoom persons="0"/>
                </capacity>
                <length meter="36.0"/>
                <width meter="2.4"/>
                <accessTime secondsPerPerson="0.25"/>
                <egressTime secondsPerPerson="0.25"/>
                <doorOperation mode="serial"/>
                <passengerCarEquivalents pce="5.2"/>
            </vehicleType>''')
        vehiclesfile.write('''
            <vehicleType id="car">
                <length meter="7.5"/>
                <width meter="1.0"/>
                <maximumVelocity meterPerSecond="40.0"/>
                <accessTime secondsPerPerson="1.0"/>
                <egressTime secondsPerPerson="1.0"/>
                <doorOperation mode="serial"/>
                <passengerCarEquivalents pce="1.0"/>
            </vehicleType>''')
        vehiclesfile.write('''
            <vehicleType id="bike">
                <length meter="5.0"/>
                <width meter="1.0"/>
                <maximumVelocity meterPerSecond="4.4704"/>
                <accessTime secondsPerPerson="1.0"/>
                <egressTime secondsPerPerson="1.0"/>
                <doorOperation mode="serial"/>
                <passengerCarEquivalents pce="0.25"/>
            </vehicleType> ''')
        vehiclesfile.write('''
            <vehicleType id="walk">
                <length meter="1.0"/>
                <width meter="1.0"/>
                <maximumVelocity meterPerSecond="1.4"/>
                <accessTime secondsPerPerson="1.0"/>
                <egressTime secondsPerPerson="1.0"/>
                <doorOperation mode="serial"/>
                <passengerCarEquivalents pce="0.0"/>
            </vehicleType> ''')

        vehc_formt = '<vehicle id="%s" type="%s"/>'

        log.info('Iterating over vehicles and writing vehicle definitions.')

        n = 0
        for car in cars:
            vehiclesfile.write(vehc_formt % car)
            n += 1
            if n % 10000 == 0:
                vehiclesfile.flush()

        vehiclesfile.write('</vehicleDefinitions>')
        vehiclesfile.close()

        log.info('Formatting outputed XML files.')
        FilesysUtil.format_xml(config['outfile'])
        FilesysUtil.format_xml(config['vehiclesfile'])

        log.info('Plans file merging complete.')
