
from xml.etree.ElementTree import iterparse, tostring
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


    def get_vehicles(self, agents, offset):
        leg_list = self.database.get_routes(agents)
        act_list = self.database.get_activities(agents)

        legs = defaultdict(list)
        acts = defaultdict(list)
        cars = set()

        for leg in leg_list:
            leg = list(leg)
            if leg[5] > 0:
                cars.add((leg[5], 'car'))
            elif leg[2] == 11:
                leg[5] = offset + leg[0]
                cars.add((leg[5], 'walk'))
            elif leg[2] == 12:
                leg[5] = offset + leg[0] * 2
                cars.add((leg[5], 'bike'))
            legs[leg[0]].append(leg)

        for act in act_list:
            acts[act[0]].append(act)

        return legs, acts, cars


    def run(self, config):
        planspath = config['planspath']

        pr.print(f'Loading plans from {planspath}.', time=True)
        parser = iterparse(planspath, events=('start', 'end'))
        parser = iter(parser)
        evt, root = next(parser)

        agent = None
        agents = set()
        count = 0

        max_vehicle = self.database.get_max('abm2018', 'vehicles', 'vehicle_id')
        offset = max_vehicle + 1

        pr.print('Iterating over plans to identify agents.', time=True)
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

        pr.print(f'Found {len(agents)} agents in plans.', time=True)
        pr.print(f'Fetching vehicular data for agent plans.', time=True)
        legs, acts, cars = self.get_vehicles(agents, offset)

        parser = iterparse(planspath, events=('start', 'end'))
        parser = iter(parser)
        evt, root = next(parser)

        outfile = open(config['outfile'], 'w')
        outfile.write('<?xml version="1.0" encoding="utf-8"?>'
            '<!DOCTYPE population SYSTEM "http://www.matsim.org/files/dtd/population_'
            'v6.dtd"><population><attributes><attribute name="coordinateReferenceSyst'
            'em" class="java.lang.String">Atlantis</attribute></attributes> ')

        agent = None
        act = []
        leg = []
        count = 0

        leg_frmt = '<leg dep_time="%s" mode="%s" trav_time="%s">'
        route_frmt = ('<route distance="%s" end_link="%s" start_link="%s" '
            'trav_time="%s" type="%s" vehicleRefId="%s">%s</route>')

        pr.print('Iterating over plans to append/modify vehicular data.', time=True)
        for evt, elem in parser:
            if evt == 'start':
                if elem.tag == 'person':
                    agent = int(elem.get('id'))
                    outfile.write('<person id="%s"><plan selected="yes">' % agent)
                    count += 1
                    if count % 10000 == 0:
                        outfile.flush()
                        root.clear()
                elif elem.tag == 'activity':
                    act = acts[agent].pop(0)
                    outfile.write(tostring(elem).decode('utf-8'))
                elif elem.tag == 'leg':
                    leg = legs[agent].pop(0)
                    outfile.write(leg_frmt % (
                        elem.get('dep_time'), 
                        elem.get('mode'), 
                        elem.get('trav_time')))
                elif elem.tag == 'route':
                    outfile.write(route_frmt % (
                        elem.get('distance'),
                        elem.get('end_link'),
                        elem.get('start_link'),
                        elem.get('trav_time'),
                        elem.get('type'),
                        str(leg[5]),
                        elem.text))
            elif evt == 'end':
                if elem.tag == 'person':
                    outfile.write('</plan></person>')
                elif elem.tag == 'leg':
                    outfile.write('</leg>')
                    
        outfile.write('</population>')
        outfile.close()
        del parser

        pr.print(f'Creating vehicles file at {config["vehiclesfile"]}.', time=True)

        vehiclesfile = open(config['vehiclesfile'], 'w')
        
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

        pr.print('Iterating over vehiles and writing vehicle definitions.', time=True)

        n = 0
        for car in cars:
            vehiclesfile.write(vehc_formt % car)
            n += 1
            if n % 10000 == 0:
                vehiclesfile.flush()

        vehiclesfile.write('</vehicleDefinitions>')
        vehiclesfile.close()

        pr.print('Plans file merging complete.', time=True)
