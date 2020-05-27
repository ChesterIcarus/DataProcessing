
import os
import subprocess
import logging as log

from xml.etree.ElementTree import iterparse
from shapely.geometry import Point
from shapely.wkt import dumps

from icarus.generate.network.config import Config
from icarus.util.file import multiopen, exists
from icarus.util.sqlite import SqliteUtil


class Network:
    def __init__(self):
        pass

    
    def ready(self, network):
        ready = True
        schedule_files = ('agency.txt', 'calendar_dates.txt', 'calendar.txt',
            'frequencies.txt', 'routes.txt', 'shapes.txt', 'stops.txt',
            'stop_times.txt', 'transfers.txt', 'trips.txt')
        pathjoin = lambda x: os.path.join(network['roads']['schedule_dir'], x)
        schedule_files = tuple(map(pathjoin, schedule_files))
        network_files = (
            network['roads']['osm_file'],
            network['roads']['osmosis'],
            network['roads']['pt2matsim'],
            *schedule_files
        )
        for network_file in network_files:
            if not exists(network_file):
                log.warn(f'Could not find files {network_file}.')
                ready = False
        return ready

    
    def complete(self, folder):
        path = lambda x: os.path.join(folder, x)
        files = ('input/transitVehicles.xml.gz', 'input/transitSchedule.xml.gz', 
            'input/network.xml.gz')
        complete = False
        for f in files:
            if os.path.exists(path(f)):
                log.warn(f'Found file {f} already generated.')
                complete = True
        return complete


    def cleanup(self, folder):
        path = lambda x: os.path.join(folder, x)
        subprocess.run(('gzip', '-q', path('input/network.xml')), check=True)
        subprocess.run(('gzip', '-q', path('input/transitSchedule.xml')), check=True)
        subprocess.run(('gzip', '-q', path('input/transitVehicles.xml')), check=True)
        subprocess.run(('rm', '-r', path('tmp/')), check=True)


    def map(self, folder, pt2matsim, memory):
        path = lambda x: os.path.join(folder, x)
        subprocess.run((
            'java', f'-Xmx{memory}', 
            '-cp', pt2matsim, 'org.matsim.pt2matsim.run.PublicTransitMapper',
            path('config/map.xml')), check=True)


    def transit(self, folder, pt2matsim, memory):
        path = lambda x: os.path.join(folder, x)
        config = path('config/transit.xml')
        subprocess.run((
            'java', f'-Xmx{memory}', 
            '-cp', pt2matsim, 'org.matsim.pt2matsim.run.Osm2MultimodalNetwork',
            config), check=True)


    def schedule(self, folder, pt2matsim, epsg, schedule, memory):
        path = lambda x: os.path.join(folder, x)
        subprocess.run((
            'java', f'-Xmx{memory}', 
            '-cp', pt2matsim, 'org.matsim.pt2matsim.run.Gtfs2TransitSchedule',
            schedule, 'dayWithMostServices', f'EPSG:{epsg}', 
            path('tmp/schedule.xml'), 
            path('input/transitVehicles.xml')), check=True)
    

    def trim(self, folder, osmosis, pbf, threads):
        path = lambda x: os.path.join(folder, x)
        config = path('config/trim.poly')
        osm = path('tmp/network.osm')
        subprocess.run((
            osmosis, 
            '--read-pbf-fast', f'workers={threads}', f'file={pbf}', 
            '--bounding-polygon', f'file={config}', 
            '--tag-filter', 'accept-ways', 'highway=*', 'railway=*', 
            '--tag-filter', 'reject-relations',
            '--used-node', 
            '--write-xml', osm), check=True)


    def generate(self, folder, network, resources):
        path = lambda x: os.path.join(folder, x)
        os.makedirs(path('tmp'), exist_ok=True)
        os.makedirs(path('input'), exist_ok=True)
        os.makedirs(path('config'), exist_ok=True)

        log.info('Generating network configuration files.')
        Config.configure_trim(folder, network['roads']['region'])
        Config.config_map(folder, network['roads']['subnetworks'])
        Config.configure_transit(
            folder,
            network['epsg'],
            network['units'],
            network['roads']['highways'],
            network['roads']['railways'],
            network['roads']['subnetworks'])

        log.info('Trimming pbf to selected region.')
        self.trim(
            folder,
            network['roads']['osmosis'],
            network['roads']['osm_file'],
            resources['cores'])
        
        log.info('Extracting transit schedule from Valley Metro data.')
        self.schedule(
            folder,
            network['roads']['pt2matsim'], 
            network['epsg'], 
            network['roads']['schedule_dir'],
            resources['memory'])

        log.info('Generating multimodial network .')
        self.transit(
            folder,
            network['roads']['pt2matsim'],
            resources['memory'])

        log.info('Mapping transit routes/schedules onto network.')
        self.map(
            folder,
            network['roads']['pt2matsim'],
            resources['memory'])

        log.info('Cleaning up.')
        self.cleanup(folder)
