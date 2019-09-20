from collections import defaultdict
from xml.etree.ElementTree import iterparse

filepath = '/home/Shared/matsim/run1/input/network.xml'
context = iterparse(filepath, events=('start', 'end'))
context = iter(context)
event, root = next(context)

freespeeds = defaultdict(int)
count = 0

for evt, elem in context:
    count += 1
    if evt == 'end' and elem.tag == 'link':
        freespeeds[elem.get('freespeed')] += 1
    if count >= 100000:
        root.clear()