
import os
import subprocess
import logging as log

from xml.etree.ElementTree import iterparse
from shapely.geometry import Point
from shapely.wkt import dumps

from icarus.util.file import multiopen
from icarus.util.sqlite import SqliteUtil


class Network:
    def __init__(self, folder: str):
        self.folder = folder
        self.path = lambda x: os.path.join(folder, x)

    
    def ready(self):
        return True

    
    def complete(self):
        files = ('input/transitVehicles.xml', 'input/transitSchedule.xml', 'input/network.xml')
        check = lambda x: os.path.exists(self.path(x))
        return all(map(check, files))


    def cleanup(self):
        pass


    def configure(self, region):
        with open(self.path('config/trim.poly'), 'w') as f:
            f.writelines(('network\n', 'first_area\n'))
            f.writelines((f'{pt[0]}\t{pt[1]}\n' for pt in region))
            f.writelines(('END\n', 'END\n'))


    def map(self, pt2matsim):
        subprocess.run((
            'java', '-Xms4G', '-Xmx8G', 
            '-cp', pt2matsim, 'org.matsim.pt2matsim.run.PublicTransitMapper',
            self.path('config/map.xml')), check=True)


    def transit(self, pt2matsim):
        subprocess.run((
            'java', '-Xms4G', '-Xmx8G', 
            '-cp', pt2matsim, 'org.matsim.pt2matsim.run.Osm2MultimodalNetwork',
            self.path('config/transit.xml')), check=True)


    def schedule(self, pt2matsim, epsg, schedule):
        subprocess.run((
            'java', '-Xms4G', '-Xmx8G', 
            '-cp', pt2matsim, 'org.matsim.pt2matsim.run.Gtfs2TransitSchedule',
            schedule, 'dayWithMostServices', f'EPSG:{epsg}', 
            self.path('tmp/schedule.xml'), 
            self.path('input/transitVehicles.xml')), 
            check=True)
    

    def trim(self, osmosis, osm):
        subprocess.run((
            osmosis, 
            '--read-pbf-fast', 'workers=4', f'file={osm}', 
            '--bounding-polygon', 'file=' + self.path('config/trim.poly'), 
            '--tag-filter', 'accept-ways', 'highway=*', 'railway=*', 
            '--tag-filter', 'reject-relations',
            '--used-node', 
            '--write-xml', self.path('tmp/network.osm')), check=True)


    def generate(self, osm, schedule, region, epsg, pt2matsim, osmosis):
        log.info('Generating network configuration files.')
        self.configure(region)

        log.info('Trimming pbf to selected region.')
        self.trim(osmosis, osm)
        
        log.info('Extracting transit schedule from Valley Metro data.')
        self.schedule(pt2matsim, epsg, schedule)

        log.info('Generating multimodial network .')
        self.transit(pt2matsim)

        log.info('Mapping transit routes/schedules onto network.')
        self.map(pt2matsim)

        log.info('Cleaning up.')
        self.cleanup()
