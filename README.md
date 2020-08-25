
# Icarus

## About

This repository is a collection of python scripts for the simulation platform Icarus designed to prepare the MAG ABM dataset to be simulated in MATSim and analyze the results of said simulation with exposure data.

- [Installation](#installation)
- [Files](#files)
- [Database](#database)
- [Running](#running)
- [Processes](#processes)

## Installation

This repository is organized and installed as a local python package and has several other python and non-python dependencies. Most of the dependencies can be satisified automatically on install if using `pip` as your python package installer; these dependencies are listed in `requirements.txt`. However, before `rtree` can be installed, `libspatialindex` also needs to be installed, which has binaries avaiable [here](https://libspatialindex.org/) or on many popular package mangers (conda, apt, pacman, etc.). Again, pip will fail to install `rtree`, a dependcy of this package, if `libspatialindex` is not first installed and added to the environment path.

As an example, demonstrated here is the process for installing icarus with Anaconda using a unix-like shell. First, install Anaconda and add it to the environment path. Then create an python 3.7 conda environment for the project and activate it.

```bash
conda create --name icarus python=3.7
conda activate icarus
```

Then install `libspatialindex` as mentioned above using Anaconda (Windows), apt (Debian) or Homebrew (MacOS).  

```bash
(Windows)   conda install -c conda-forge libspatialindex
            conda install -c conda-forge rtree
(Debian)    sudo apt install libspatialindex-dev
(MacOS)     brew install spatialindex
```

With the essential dependencies met, the `icarus` package cn now be installed. Navigate to the preferred location to download this repository and then download and install it using `git` and `pip`. If any of the scripts in the repository are altered, the package will have to be reinstalled using `pip` before the changes will take effect.

```bash
git clone https://github.com/ChesterIcarus/DataProcessing.git
pip install icarus-python
```

To use the developmental build, download and checkout the `dev` branch and then install with `pip` again. This branch will have the new updates, but not everything here is guarenteed to be stable. To download a specific release, fetch all tags and then checkout the desired tag, or go to the releases page and download the zip file with the source code for the package.

```bash
git fetch
git checkout -t origin/dev
```

You will also need to download [osmosis](https://github.com/openstreetmap/osmosis/releases/) and [pt2matsim](https://bintray.com/polettif/matsim/pt2matsim/) from their respective sources as well as the source data (daymet, MAG ABM, etc.) and the custom built 12-SNAPSHOT JAR of MATSim from the Dropbox.

## Files

## Database

A detailed explanation of the database structure used in icarus can be found on [dbdocs.io](https://dbdocs.io/benjaminBrownlee/icarus). This site provides full explanations for all tables and fields as well as their relationships with each other in visual format. However, dbdocs is a fairly new site and its services are still in beta, so the `database.dbml` file is an alternative resource with the same information (in fact, this file is what generates the hosted webpage).

## Running



## Processes

The rounded boxes represent processes, which have input (arrows pointing towards) and output (arrows pointing away) data. The squared boxes represent data, which can be an input to (arrows pointing away) and ouput of (arrows pointing towards) processes. Green and purple boxes represent python and java process respectively while red and blue boxes represent xml files and sql tables respectively.

![dependency diagram](https://github.com/ChesterIcarus/DataProcessing/blob/dev/docs/dependencies.png)

### parse regions

The term regions is an alias for the microanalysis zones (MAZs) used by the MAG ABM. Of course, when Icarus is applied to locations other than Phoenix, the regions will coorespond to whatever set of regions is used to define the trips in that dataset. Region data is distributed in a shape/database file pair; these regions are parsed, transformed and saved to a table named `regions`. See the schema for the table as documented above for more details. While the code for parsing regions supports CRS transofrmation, its is currently hardcoded to assume the shapefile is in EPSG:2223 and the desired output is EPSG:2223.

### parse abm

The MAG ABM data is delivered in a CSV format in three files: households, trips and persons. These files are read and loaded into the tables `households`, `trips` and `persons` respectively with almost no alteration. See the MAG ABM documnetation for more details regarding the ABM data.

### generate network

The network that MATSim will simulate the population of Maricopa on is based on OpenStreeMap road data and ValleyMetro transit data. Make sure that you have both the OSM PBF for Arizona as well as the transit files from ValleyMetro downloaded and linked to in the project configuration file. However, a lot of processing has to occur before these can become valid input for the simulation. The `generate network` process will spawn `osmosis` and `pt2matsim` process to:

1. Generate configuration files for the network generation from the project config file.
2. Decompress PBF file into OSM file and trim the network to a specified region.
3. Generate a MATSim transit schedule from the ValleyMetro transit data.
4. Convert the OSM network into a MATSim XML mulitmodial network; configure the allowed modes on the XML network.
5. Map the transit schedule onto the XML network, tweaking the network with artificial links if needed.
6. Compress output file and delete itermediary/temporary files.

Make sure that the `osmosis` and `pt2matsim` fields in the project config accurately reflect the location of the binaries on your machine. The `schedule_dir` should point to the location of the VallyMetro data, and the `osm_file` should point to the location of the source PBF file from OpenStreetMap. The map is trimmed using the specified region in `region`, which is a list of WGS84 lat/lon coordinates with the first and last point coinsiding. The map will then be transformed to the epsg coordinate system specified in `epsg` (also specify "meters" or "feet" in `units` for the target coordinate system); the defualt is epsg:2223, which is centered over and optimized for Arizona. The `subnetworks` dictionary is the set of routable modes in the network mapped to the modes that each mode can be routed with. The `highways` and `railways` dictionaries map all the chosen link types to the sets of valid modes for each type. With exception to the file paths, most of these settings probably do not need to be altered.

The end result are the network, transit schedule and transit vehicles files in the input folder as well as three files in the config file. The latter are merely for reference and will not be used again by any other script.

As a word of warning, make sure that the resources in the `resources` option in the configuration file represent the maximmum resources you want processes to take at any given time. If these numbers are too large, some process may be allocated more memory than your system can afford, which can lead to crashes. While this is true anywhere, these processes are particularly resource intensive.

### parse roads

After a network has been generated, it is useful to have the road information in an accessible format as we analyze agent movement and exposure across it. From the `input/network.xml.gz` file, the tables `links` and `nodes` are extracted; see table information for more details. Each link has fields for an air temperature and mrt temperature profile, which remain null until the parsing processes for each are run.

### parse parcels

The county has information available regarding all the parcels in Maricopa county. These locations can be used in the simulation as locations that agents can travel between. Parcels can be either residential, commercial or other (which is actually unknown), and a defualt fake parcel is generated for each region as failsafe for some operations. These are saved in the `parcels` table. Like the network, this data is stored in a pair of database/shape files, and the parcels parsed with the region data inorder to assign each parcel a region. Consequently, parcel parsing is also extremely slow for the same reasons, taking about two hours on my machine. 

### parse daymet

Daymet is a collection of minimum and maximum temperature readings for every square kilometer and every day in North America taken via satellite since 1980. This data is distriubted by the tile (a unit of geographic region) in pairs of netCDF files, one containing the minimum temperatures for each day for a year and the other containing the maximum values. In this process, a set of files coorseponding with the selected daymet tiles are selected as well as a desired day and number of steps, as specified in the configuration file. All the locations of the temperature readings are extracted and used to populate a spatial index. Due to the low granularity of the temperature data and the relative uniformity of air temperature data, only a few unique combinations of minimum and maximum temperature pairs exist; each of these distinct pairs of values and the subsequent values calculated from them are referred to as a temerature profile. Then, all the links and parcels in the database are loaded in and the nearest temperature reading location is calculated for each them, which is written back to the database. While daymet only distributes the minimum and maximum daily temperatures, a full day of air temperatures can be estimated using the diurnial air temperature estimation process. The temperatures for the entire day are calculated and used to populate the new `air_temperatures` table. A few additional constant temperature profiles are generated for indoor temperatures of parcels with air conditioning.

The `tmax_files` and `tmin_files` parameters are lists of cooresponding file locations to the netCDF files for the daymet tiles. The `day` parameter chooses the day of the Julian calendar from the datatset while the `steps` parameter chooses the number of temperature readings to calculate from the minimum and maximum temperature. When downloading netCDF files, only select tiles of the smallest granularity; larger tiles become exponentially more expensive to iterate and process (and generally very few daymet locations are need to cover a desired region). This process supports coordinate transformation, but like the regions parsing the current implementation has the transoformation hardcoded to transofrm EPSG:4326 to EPSG:2223.

### parse mrt

The MRT temperature dataset is a set of nearly four million points in Maricopa county where Google street view images have been analyzed and evaluated for several temperature metrics: mean radiant temperature (MRT), physiological equivalent temperature (PET) and universal thermal climate index (UTCI). These values have been calculated for 15 minute intervals in daylight hours; outside of daylight hours, these values are assumed to be the same as the air temperature. The mrt parsing tools performs the following steps:

1. Load the network nodes and links into the process.
2. Load the first temperature file (any timestamp will do).
2. Parse the temeprature reading locations and load them into a spatial index.
3. Iterate over the links and locate all mrt points within a specified range of the link; every link is associated with a profile of a unique set of mrt points.
4. Write the links, now updated with mrt profile information, back to the database.
5. Evaluate the exposure for a profile by averaging the values for the points that make up the profile.
6. Write the results to the `mrt_temperatures` table in the database.
7. Load in another mrt temperature file (a new timestamp).
8. Repeat steps 4 through 6 until all mrt files have been parsed.

Parcels could be added to this process much like how they are in the daymet parsing proces, but to be usefully applied, activities at particular parcel types would need to have strong estimations as to whether they are outside (like a park) or indoor (like an unconditioned warehouse). See the `mrt_temperatures` for more details regarding the output of this process.

### generate population

Before a simulation can be run, the ABM data needs to transformed into a population that can be written as MATSim input files. Population generate does several things:

1. Forms parties and groups from shared trips information.
2. Filters out trips and agents by conditions that user desires (particular modes or activity types).
3. Filters out trips and agents if they don't make sense to us (bad timing, unknown regions, no driver, etc.).
4. Filters out trips and agents if we deem the trip unrealistic to be made in simulation.
5. Filters out trips and agents recursively by party and group affiliation according the previous three conditions.
6. Assigns parcels to activities based on group affiliation.
7. Gives all valid activities, legs and agents unique identifcation numbers.

The desired modes and activity types can be specified using the `modes` and `activity_types` options in the configuration file. Experimentation has shown that there are very few trips that don't simply make sense; this was mostly needed for back when the ABM data had much less accurate timing. A trip is deemed unrealistic if the minimum speed of the trip -- shortest direct distance betweeen regions divided by the trip duration -- grossly exceeds the maximum speed for a mode of transport. These types of issues should also be a neglible amount of the data.

Each trip is broken into activities and legs, where activities are events happening beween legs or events of travel. Every leg is given a party and each group is given a group. If two trips are shared, meaning the ABM specifies that the agents are to travel together, the cooresponding legs are assigned to the same party, and the corresponding activities before and after the legs are assigned to the same groups. This allows parcels to be assigned to groups, which will automatically ensure that agents who are suppose to be travelling together are assigned the same locations.

As alluded to earlier, in order for an agent to be valid, all his modes and activitiy types must be a subset of those specified by the user, all regions of his activites must be a subset of the known regions, all his legs must have a reasonable minimum speed, and all parties of a vehiclular mode must have a driver. This logic is best summarized as such,

```python
def valid_party(party: Party) -> bool:
    return party.driver is not None or party.mode != RouteMode.CAR

def valid_leg(leg: Leg) -> bool:
    distance = network.minimum_distance(leg.party.origin_group.maz, leg.party.dest_group.maz)
    duration = leg.end - leg.start
    valid = False
    if duration > 0:
        valid = distance / duration < leg.mode.route_mode().max_speed()
    elif distance == 0:
        valid = True
    return valid

def valid_agent(agent: Agent) -> bool:
    return (
        agent.modes.issubset(modes)
        and agent.activity_types.issubset(activity_types)
        and agent.mazs.issubset(network.mazs)
        and all(valid_party(party) for party in agent.parties)
        and all(valid_leg(leg) for leg in agent.legs)
    )
```

When an agent is invalid, all agents that are recursively dependent on the agnet need to be removed also. Dependednts are the agents who are part of parties in which the agent is the driver for. Theoretically, an agent being removed could set off a massive chain of dependent removals, but for the most part dependents tend to be young family members. The effect of recursively removing agents is only significant when modes are constricted considerably.

Households are assigned a single parcel, prefferable a residential parcel. Only once all parcels have been exhausted will multiple households be assigned the same parcel. All groups specified as home will use the agent's household parcel. All other groups are assigned a parcel randomly, prefferably a commercial parcel. When a region contains no residential parcels, households are assigned commercial parcels randomly. When a region contains no commercial regions, groups are assigned residential parcels randomly. Other and default parcels are used a last resort in the case of both conditions.

### generate plans

After a population has been generated, a plans file needs to be generated, which will become an important par to of the input to the MATSim simulation. Because the population generation organized trips into `activities` and `legs`, which is how MATSim organizes plans, this process is quite simple. All that needs to be done is to pull the data from the tables, refactor some naming, and add any changes to virtualized/teleported modes. Plans generation also has options for choosing a sample of population; these options can be found in the `sample` section of the configuration file. The `sample_size` option will select at most that many agents if specified while the `sample_percent` will select at least that proportion of the agents of the population. If both are specified, the minimum value will be used. The other options refer to the columns on the `agents` table. If "true" is specified, then only agents with this attribute will be selected, while if "false" is specified only agents without this attribute are selected. Otherwise ("null" or unspecified), agents will be selected regardless of this attribute. All attribute selections are conjunctive. If you need a more specific type of population selection, you will need to modify the source code.

The chosen plans are formatted to the MATSim [plans file specifications (v4)](http://www.matsim.org/files/dtd/plans_v4.dtd) and then saved to `input/plans.xml.gz`.

### generate config

The MATSim simulation takes a fairly long and complex XML config file to describe and control the nature of the simulation. This process will read the project configuration file and produce a MATSim configuration file and save it at `input/config.xml`.

While I have made a process that reproduces my given config using variables from the project config file, there are many other variables in the MATSim configuration that could be tweaksed that aren't accessible through this tool. Also, since simulations are rather complicated and many types exist, I was not able to thoroughly test the reliability of this tool under different simulation configurations. If you struggle to get you config to work correctly or need to change something not explicitly clear in the project confi, please contact me (it's not worth stressing over the MATSim doucmentation).

### simulation

Assuming that all the dendencies for the simulation have been met, the simulation can be run by,

```bash
java -Xms32G -Xmx64G \
    -cp /path/to/matsim/jar \
    org.matsim.run.Controler /path/to/matsim/config
```

Note the they demanded resources in the first line can vary based on the size of the simulation being run, but should never be specified higher than what the machine/instance running can provide (this can lead to crashes).

The simulation runs well if you have the following file structure,

```files
run_xx_xx_xx/
    input/
        config.xml
        network.xml.gz
        plan.xml.gz
        transitSchedule.xml.gz
        transitVehicles.xml.gz
        vehicles.xml.gz
    output/
```

where the output directory will be where the simulation outputs the simulation results (assuming that the simulation is started from this working directory). You will notice that this reflects the project structure well, so the simulation can be run from the project directory with ease. If the simulation is run elsewhere, just zip the input folder and bring it along with the MATSim JAR. If you change the file structure, you may need to modify the paths in the XML config file so the simulation can find the input data.

Note that unless you are debuging the simulation with it, `output/ITERS/` can be deleted. This folder can be very large, especially if the simulatin was run for many iterations, so deleting it can save a lot of space and transfer time.

### parse events

Once the simulation data has been obtained, it now has to be parsed and imported back into the database. The `output_plans` file contains all the legs and activities of the agents in the simulation much like the input plans file, but none of the timing of the plans file is accurate and it does not include link level timing. This is why the `output_events` file, which is a massive document of all the events that occured in the entirity of the simulation needs to be iterated and parsed. Parsing events will use both these files and information from the database in the following process:

1. Load the network data in from the database.
2. Load the routing data in from the output_plans file.
3. Load in the identifiers for activities and legs from the database.
4. Iterate over the events and parse activities, legs and events from the data.
5. Push the results back to the database.

The fourth step is expensive as the events file is enormous and a lot of data is being extracted from it. Consequently, the events parsing will frequently pause and export any compleeted legs, activities and events to the database to save memory in the parsing process. It may take a while to parse the simulation, but the log should keep you updated on its process. There are also some complicated things occuring in the handling of virtualized, vehicular and transit legs (if enabled), as well as some mode refactoring. The results are saved in `output_agents`, `output_legs`, `output_activities` and `output_events`; see the table descriptions for more details. You will notice that these tables mirror the corresponding input tables witgh exception to the events; there are no input events, the name was simple chosen for consistency.

### analyze exposure

The exposure analysis tool uses the daymet temperature data and the results of the simulation to calculate agent exposure at an event level, when possible. If event level data is not available for a particular route, the temperature at the link of the starting activity is used. Some travel is air conditioned, so indoor temperatures are used for exposure. The exposure analysis tool will load the network data from database and then iteratively calculate the exposure for each agent in batches of 100k agents. Since the events and exposure parsing tools have already done most of the heavy lifting in parsing, the exposure tool is actually quite quick.

Results are saved back to the original output tables. Since updates in SQL are slow, it is actually much faster to create new temporary tables, drop the old ones and rename the new ones. The only side affect of this is that sqlite may change the schema slightly to reflect the simplified sqlite typing; this will have no functional affect on the database, and it can be readily changed if it is an issue. Since large tables are being created and dropped (and can be done so repeatedly if running multiple exposure analysis runs), it may be worth seeing the [storage remark](#minimizing-storage) in the notes section.
