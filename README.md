
# Icarus Simulation Data Processing

## About

## Building

This project is organized as a python package. Clone this repository and then install it using pip. Also see the requirements file for additional dependencies that may be needed to run certain modules.

```bash
    git clone https://github.com/ChesterIcarus/DataProcessing.git
    pip install DataProcessing
```

Note that there exists more dependencies beyond those in python installed by pip. All source data and helper programs will need to obtained and linked to in the configuration folder.

## Project Structure

This package has a collection of scripts which can prepare simulation input data and analyze output data. A given simulation run has a folder dedicated to it where all modules need to be executed from; these modules will read and write from files inside this folder, as well as read other files and execute other programs specified in the config file.

Here is a run down of the internal structure of a simulation run folder.

### Files

#### config.json

This is the master configuration file which describes how the simulation ought to be constructed and executed. Every module will reference the config file to locate external source data and executeables as well as information regarding how it should run. While some attributes of the simulation are hardcoded into the scripts and some other externl configuration files are still needed, these are temporary hacks done to keep the project moving forward; the eventual goal is to have this file and this file alone contain every attribute that we may possibly want to tweak.

#### database.db

This is the master data file which contains all the project data stored in a sqlite database. Previously we had used an SQL database for hosting our data, but technical issues with getting users access to the database lead to this more modular solution. Everything that the project uses, including intermediary data, is saved in this database, which can lead to it being quite large (typically between five and seven gigabytes). Of course, particular data of interest can be export as CSV or its own database at on request. Descriptions of al tables in this database are given below.

#### config/

This folder includes additional configuration files used in some process (such as the network generation). This is partly a consequence of the fact that not all steps of data preparation are done entirely in house, so some external software needs to be run with special configuration files. Eventually these files will be generated temporarily form the information in the master configuration file, but only when time permits.

#### input/

This folder includes all the files needed to run a MATSim simulation. After the files have been generated, this file can be zipped an sent else where to handle the simulation. The only other thing needed to run the simulation is an installation of Java and the matsim JAR.

#### output/

This folder includes all the files that the MATSim simulation spits out. The only important files to the data processing in the this project are the events, plans, vehicles, network, and logfile files. The iterations folder can be deleted in its entirity (and doing so save you enormous amounts of time and storage).

#### result/

This folder includes all visuals and summaries drawn from the project data. The actual contents of this folder may vary.

#### temp/

Location where processes may save temporary files. Generally files are deleted after the process completes, so this folder will usually remain empty, but do not put any files in this directory since processes may overwrite them with no warning.

### Tables

#### trips

This table cooresponds exactly, without alteration, to the trip data delivered in the ABM trips csv file. See the ABM documentation for more details regarding fields in this table.

#### households

This table cooresponds exactly, without alteration, to the household data delivered in the ABM households csv file. See the ABM documentation for more details regarding fields in this table.

#### persons

This table cooresponds exactly, without alteration, to the person data delivered in the ABM trips csv file. See the ABM documentation for more details regarding fields in this table.

#### agents

This table links the input data of the simulation to the ABM data. All agents that are deemed valid under the conditions set by the population generation will be populated here. The new unique `agent_id` field can be used to connect agents to their activities and legs while the original `household_id` and `household_idx` fields can be used to link these agents back to the original persons in the ABM data.

| field         | schema             | description                                                                   |
|---------------|--------------------|-------------------------------------------------------------------------------|
| agent_id      | mediumint unsigned | uniquely identifying field                                                    |
| household_id  | mediumint unisnged | household identifier, linked to `hhid` in ABM tables                          |
| household_idx | smallint unsigned  | uniquely identifying field within a household, linked to `pnum` in ABM tables |
| plan_size     | tinyint unsigned   | total number of activities and legs                                           |
| uses_vehicle  | tinyint unsigned   | 1 if agent has a personal vehicle leg, 0 otherwise                            |
| uses_walk     | tinyint unsinged   | 1 if agent has a walking leg, 0 otherwise                                     |
| uses_bike     | tinyint unsinged   | 1 if agent has a biking leg, 0 otherwise                                      |
| uses_transit  | tinyint unsigned   | 1 if agent has a transit leg, 0 otherwise                                     |
| uses_party    | tinyint unsigned   | 1 if agent has a leg part of a party, 0 otherwise                             |

#### activities

Originally activities were described in the ABM trips table along with legs. After being parsed, assigned groups, filtered, cleaned and prepared, activities are extracted from trips and given a table of their own. Each activity has its own unique `activity_id`, but more useful are the `agent_id` and `agent_idx` fields, which link the activities to their respective agents in `agents`. The `group` field is a unique id that links together activities that needed to be assigned APNs together due to party restrictions; a group of zero means the activity was assigned an APN independent of all other activities.

Every agent will have a `plan_size` of `2n+1`, which will mean the agent has `n+1` activities in the `activities` table and `n` legs in the `legs` table. For a leg with `leg_idx` of `n`, the activity preceding the leg has an `activity_idx` of `n` and that proceding the leg has one of `n+1`.

| field       | schema             | description                                                      |
|-------------|--------------------|------------------------------------------------------------------|
| activtiy_id | mediumint unsigned | uniquely identifying field                                       |
| agent_id    | mediumint unisnged | agent identifier, linked to `agent_id` on `agents`               |
| agent_idx   | smallint unsigned  | uniquely identifying field within an agent, sequenced temporally |
| type        | varchar            | type of activity                                                 |
| apn         | varchar            | parcel identifier, linked to `apn` on `parcels`                  |
| group       | mediumint unsigned | APN spawning group identifier; 0 for no group                    |
| start       | mediumint unsigned | start time of activity in seconds from midnight                  |
| end         | mediumint unsigned | end time of activity in seconds from midnight                    |
| duration    | mediumint unsigned | duration of activity in seconds                                  |

#### legs

Originally legs were described in the ABM trips table along with activities. After being parsed, assigned parties, filtered, cleaned and prepared, legs are extracted from trips and given a table of their own. Each leg has its own unique `leg_id`, but more useful are the `leg_id` and `leg_idx` fields, which link the legs to their respective `agents`. The `party` field is a unique id that links together legs that are travelling together; a party of zero means a leg is travelled alone. See the activities cetion for more details regarding sequencing activities and legs.

| field     | schema             | description                                                      |
|-----------|--------------------|------------------------------------------------------------------|
| leg_id    | mediumint unsigned | uniquely identifying field                                       |
| agent_id  | mediumint unisnged | agent identifier, linked to `agent_id` on `agents`               |
| agent_idx | smallint unsigned  | uniquely identifying field within an agent, sequenced temporally |
| mode      | varchar            | leg mode type                                                    |
| party     | mediumint unsigned | APN spawning party identifier; 0 for no group                    |
| start     | mediumint unsigned | start time of leg in seconds from midnight                       |
| stop      | mediumint unsigned | stop time of leg in seconds from midnight                        |
| duration  | mediumint unsigned | duration of leg in seconds                                       |

#### regions

#### centroids

#### temperatures

#### links

#### nodes

## Running

Once the repository has been installed using pip, various processes can be run using the following command structure:

```bash
    python -m icarus.[action].[item] [--folder /path/to/folder] [--replace]
```

The `--folder` argument is used to specify the location of the folder that the run data is in; without it it is assumed that the working directory is the location of the data. If the folder in question is missing important data, the process will most likely fail. The `--replace` argment is used to force data replacement. If this argument is present, the user will not be prompted before deleting previous data.

Most commands do not take additional arguements to control the nature of the process's execution. The master configuration file (see above in files) should have all the settings that can be set for each process.

| action | item | description | dependencies |
|----------| - | - | - |
| parse    | abm | parses the ABM data into the trips, households and persons tables | - |
| parse    | regions | parses MAZ region data into the regions table | - |
| parse    | network | parse the network file into the links and nodes tables | network generation |
| parse    | events | parse
| generate | plans | | - |
| generate | config | | - |
| generate | network | | - |
| generate | population | generate simulation population from ABM data and save the result as the agents, activitities and legs tables | ABM, regions and parcel parsing |
