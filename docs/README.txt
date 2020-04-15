
=========================
MATSim Simulation Results
=========================

owner:      Benjamin Brownlee
contact:    benjamin.brownlee1@gmail.com
run:        run_20_04_04
created:    04-04-2020
updated:    02-08-2020


--------
OVERVIEW
--------

This documentation is a quick summary of the input and output files used in the
simulation of Maricopa county. This documentation is not wholistic, but is intended
to describe the nature of the data enough such that someone could begin to analyze
it a bit. Please let me know if anything is incorrect, missing or unclear.


-----
FILES
-----

[./]

database.db

This is everything. All data that is ever used in this project is parsed into
here (with exception to the valley metro transit schedule). The tables in this
database can be broken down into three main categories: network, ABM, input and 
output. See the tables section for details and schema breakdowns.


config.json




[./input]

config.xml

This is the config file passed to MATSim that tells the program how to run the 
simulation. This file is generated from information in the master config file
in the root directory of this project. You may find that file more helpful
in understanding the simulation since the MATSim config file is bloated with
many different settings. Regardless, information on this file can be found in
the MATSim documentation packet.

plans.xml.gz

This file describes the plans of the agents in the simulation, or what every
actor is supposed to be doing throughout the simulation. It is just a reduced
and xml formatted version of the data in the agents, activities and legs tables
in the database file.

network.xml.gz

The network that everything is being simulated on. It contains all roads and
paths in the greater Maricopa county region marked on openstreet map and is 
labelled with traffic constraining propertied (road types, traffic signals,
speed limits, etc.). It has also been modified with some artificial links to
be functional with the Valley Metro transit schedule.

vehicles.xml.gz



transitVehicles.xml.gz

transitSchedule.xml.gz

[./output]



[./results]


------
TABLES
------

