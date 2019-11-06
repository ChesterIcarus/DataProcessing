
from xml.etree.ElementTree import iterparse
from collections import defaultdict

from icarus.input.merger.database import PlansMergerDatabase
from icarus.util.print import Printer as pr

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

    def run(self, config):
        planspath = config['planspath']

        parser = iterparse(planspath, events=('start', 'end'))
        parser = iter(parser)
        evt, root = next(parser)

        agent = None
        agents = []
        count = 0

        for evt, elem in parser:
            if evt == 'start':
                if evt == 'person':
                    agent = int(elem.get('id'))
                    agents.append(agent)
                    count += 1
                    if count % 10000 == 0:
                        root.clear()
        root.clear()
        parser.close()

        leg_list = self.database.get_routes(agents)
        act_list = self.database.get_activities(agents)
        legs = defaultdict(list)
        acts = defaultdict(list)
        cars = set()
        for leg in leg_list:
            legs[leg[0]].append(leg)
            if leg[5] > 0:
                cars.add(leg[5])
        for act in act_list:
            acts[act[0]].append(act)
        del leg_list
        del act_list

        parser = iterparse(planspath, events=('start', 'end'))
        parser = iter(parser)
        evt, root = next(parser)

        agent = None
        act = []
        leg = []
        count = 0

        for evt, elem in parser:
            if evt == 'start':
                if elem.tag == 'person':
                    agent = int(elem.get('id'))
                    count += 1
                    if count % 10000 == 0:
                        root.clear()
                elif elem.tag == 'activity':
                    act = acts[agent].pop(0)
                    elem.set('end_time', self.time(act[3]))
                    if elem.get('start_time', default=None) is not None:
                        elem.set('start_time', self.time(act[2]))
                elif elem.tag == 'leg':
                    leg = legs[agent].pop(0)
                    elem.set('dep_time', self.time(leg[3]))
                    elem.set('trav_time', self.time(leg[4]))
                elif elem.tab == 'route':
                    elem.set('trav_time', self.time(leg[4]))
                    elem.set('vehicleRefId', leg[5])
        root.clear()
        parser.close()

        vehiclesfile = config['vehiclesfile']
        
        vehiclesfile.write('<?xml version="1.0" encoding="UTF-8" ?>'
            '<vehicleDefinitions xmlns="http://www.matsim.org/files/dtd" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xsi:schemaLocation="http://www.matsim.org/files/dtd '
            'http://www.matsim.org/files/dtd/vehicleDefinitions_v1.0.xsd">')
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

        for car in cars:
            vehiclesfile.write(vehc_formt % (car, "car"))

        vehiclesfile.flush()

        vehiclesfile.write('</vehicleDefinitions>')
