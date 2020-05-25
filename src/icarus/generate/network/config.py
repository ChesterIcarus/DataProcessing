
import os

from icarus.util.file import format_xml


class Config:
    @staticmethod
    def configure_trim(folder, region):
        path = lambda x: os.path.abspath(os.path.join(folder, x))
        config = path('config/trim.poly')
        with open(config, 'w') as f:
            f.writelines(('network\n', 'first_area\n'))
            f.writelines((f'{pt[0]}\t{pt[1]}\n' for pt in region))
            f.writelines(('END\n', 'END\n'))


    @staticmethod
    def configure_transit(folder, epsg, unit, highways, railways, subnetworks):
        path = lambda x: os.path.abspath(os.path.join(folder, x)) 
        config = path('config/transit.xml')
        osm_network = path('tmp/network.osm')
        xml_network = path('tmp/network.xml')

        f =  open(config, 'w')
        f.write(f'''<?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE config SYSTEM "http://www.matsim.org/files/dtd/config_v2.dtd">
            <config>
                <module name="OsmConverter" >
                    <param name="keepPaths" value="false" />
                    <param name="keepTagsAsAttributes" value="true" />
                    <param name="keepWaysWithPublicTransit" value="true" />
                    <param name="maxLinkLength" value="500.0" />
                    <param name="osmFile" value="{osm_network}" />
                    <param name="outputCoordinateSystem" value="EPSG:{epsg}" />
                    <param name="outputNetworkFile" value="{xml_network}" />
                    <param name="scaleMaxSpeed" value="false" /> ''')

        convert = lambda x: x * 3.2808399 if unit == 'feet' else x
        freespeed = {
            'motorway':         convert(33.33333333333333),
            'motorway_link':    convert(22.22222222222222),
            'trunk':            convert(22.22222222222222),
            'trunk_link':       convert(13.88888888888889),
            'primary':          convert(22.22222222222222),
            'primary_link':     convert(22.22222222222222),
            'secondary':        convert(8.333333333333334),
            'secondary_link':   convert(8.333333333333334),
            'tertiary':         convert(6.944444444444445),
            'tertiary_link':    convert(6.944444444444445),
            'unclassified':     convert(6.944444444444445),
            'residential':      convert(4.166666666666667),
            'living_street':    convert(2.777777777777778),
            'pedestrian':       convert(0.833333333333333),
            'footway':          convert(0.833333333333333),
            'path':             convert(0.833333333333333),
            'steps':            convert(0.833333333333333),
            'rail':             convert(44.44444444444444),
            'tram':             convert(11.11111111111111),
            'light_rail':       convert(22.22222222222222)

        }
        capacity = {
            'motorway':         2000.0,
            'motorway_link':    1500.0,
            'trunk':            2000.0,
            'trunk_link':       1500.0,
            'primary':          1500.0,
            'primary_link':     1500.0,
            'secondary':        1000.0,
            'secondary_link':   1000.0,
            'tertiary':         600.0,
            'tertiary_link':    600.0,
            'unclassified':     600.0,
            'residential':      600.0,
            'living_street':    300.0,
            'pedestrian':       100.0,
            'footway':          100.0,
            'path':             100.0,
            'steps':            100.0,
            'rail':             9999.0,
            'tram':             9999.0,
            'light_rail':       9999.0
        }
        lanes = {
            'motorway':         2.0,
            'motorway_link':    1.0,
            'trunk':            2.0,
            'trunk_link':       1.0,
            'primary':          1.0,
            'primary_link':     1.0,
            'secondary':        1.0,
            'secondary_link':   1.0,
            'tertiary':         1.0,
            'tertiary_link':    1.0,
            'unclassified':     1.0,
            'residential':      1.0,
            'living_street':    1.0,
            'pedestrian':       1.0,
            'footway':          1.0,
            'path':             1.0,
            'steps':            1.0,
            'rail':             1.0,
            'tram':             1.0,
            'light_rail':       1.0
        }

        for subnetwork, modes in subnetworks.items():
            allowed = ','.join(modes)
            f.write(f'''
                <parameterset type="routableSubnetwork" >
                    <param name="allowedTransportModes" value="{allowed}" />
                    <param name="subnetworkMode" value="{subnetwork}" />
                </parameterset> ''')

        for highway, modes in highways.items():
            allowed = ','.join(modes)
            f.write(f'''
                <parameterset type="wayDefaultParams" >
                    <param name="allowedTransportModes" value="{allowed}" />
                    <param name="freespeed" value="{freespeed[highway]}" />
                    <param name="freespeedFactor" value="1.0" />
                    <param name="laneCapacity" value="{capacity[highway]}" />
                    <param name="lanes" value="{lanes[highway]}" />
                    <param name="oneway" value="true" />
                    <param name="osmKey" value="highway" />
                    <param name="osmValue" value="{highway}" />
                </parameterset>''')

        for railway, modes in railways.items():
            allowed = ','.join(modes)
            f.write(f'''
                <parameterset type="wayDefaultParams" >
                    <param name="allowedTransportModes" value="{allowed}" />
                    <param name="freespeed" value="{freespeed[railway]}" />
                    <param name="freespeedFactor" value="1.0" />
                    <param name="laneCapacity" value="{capacity[railway]}" />
                    <param name="lanes" value="{lanes[railway]}" />
                    <param name="oneway" value="true" />
                    <param name="osmKey" value="railway" />
                    <param name="osmValue" value="{railway}" />
                </parameterset>''')
        
        f.write('</module></config>')
        f.close()

        format_xml(config)


    @staticmethod
    def config_map(folder, subnetworks):
        path = lambda x: os.path.abspath(os.path.join(folder, x)) 

        modes = set(mode for submodes in subnetworks.values() for mode in submodes)
        modes = ','.join(modes)
        config = path('config/map.xml')
        output_schedule = path('input/transitSchedule.xml')
        input_network = path('tmp/network.xml')
        input_schedule = path('tmp/schedule.xml')
        output_network = path('input/network.xml')

        f = open(config, 'w')
        f.write(f'''<?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE config SYSTEM "http://www.matsim.org/files/dtd/config_v2.dtd">
            <config>
                <module name="PublicTransitMapping" >
                    <param name="candidateDistanceMultiplier" value="1.6" />
                    <param name="inputNetworkFile" value="{input_network}" />
                    <param name="inputScheduleFile" value="{input_schedule}" />
                    <param name="maxLinkCandidateDistance" value="90.0" />
                    <param name="maxTravelCostFactor" value="5.0" />
                    <param name="modesToKeepOnCleanUp" value="{modes}" />
                    <param name="nLinkThreshold" value="6" />
                    <param name="numOfThreads" value="4" />
                    <param name="outputNetworkFile" value="{output_network}" />
                    <param name="outputScheduleFile" value="{output_schedule}" />
                    <param name="outputStreetNetworkFile" value="" />
                    <param name="removeNotUsedStopFacilities" value="true" />
                    <param name="routingWithCandidateDistance" value="true" />
                    <param name="scheduleFreespeedModes" value="rail" />
                    <param name="travelCostType" value="linkLength" />
                    <parameterset type="transportModeAssignment" >
                        <param name="networkModes" value="car,bus" />
                        <param name="scheduleMode" value="bus" />
                    </parameterset>
                    <parameterset type="transportModeAssignment" >
                        <param name="networkModes" value="rail,light_rail" />
                        <param name="scheduleMode" value="rail" />
                    </parameterset>
                </module>
            </config> ''')
        f.close()
        

        format_xml(config)
