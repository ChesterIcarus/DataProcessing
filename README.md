
# Icarus Simulation Data Processing

This repository is dedicated to the data processing of simulation input and output data for the MATSim traffic simulation portion of the Icarus project. This processing includes parsing source data into SQL, generating input files for simulation from SQL data, and validating data integrity in all steps of processing.

## Data Sources

The primary source of data for the Icarus simulation is the 2018 ABM data as provided by MAG for this project. The simulation also utilizes other important but more easily accessible data sources, including osm networks from openstreetmap, spacio-temporal termperature data from [FIX ME], and parcel description data from the county of Maricopa.

The follwoing nomenclature will be used throughout documentation and code when referring to data sources:

- **abm** - activity based model of Maricopa as provided by MAG
- **daymet** - spacio-temporal temperature of Arizona as provided by [FIX ME]
- **network** - road network data of Arizona as provided by openstreetmap
- **residences/commerces** - parcel data (residential and commercial respectively)
    as provided by the county of Maricopa

## Building

First, download the repository using `curl` or `git clone`. Then, to build the project, activate the python environment of your choice (if using anaconda) and
```
    pip install /path/to/repository
```
The package will be installed under the package name `icarus-simulation` and the root module will be named `icarus`. Dependencies should be automatically downloaded and resolved.

## Running

With exception to the util module, every module contains a set of submodules, which are each executable. Each submodule contains a primary class, a database util file, a configuration file, and runner file. To execute a submodule runner file
``` 
    python -m icarus.module.submodule
```
The process being run can be configured by modifying the default configuration or by adding `--config` followed by the path to your own custom config file. Note, however, in most cases, all the attributes of the default config are required and their absence in  will your own configurations will cause script failure. Also note that if you make changes to the naming scheme or structure of the database, you will have make these  changes in all configurations and database files referencing the smae database that you intend to use.  

Every runnable also comes with a `--log` option, where you may specify a path to save the ouput of the console fro the script being run. This is a feature, but do note there is not extensive error handling or descriptive debugging, so it is not extremely useful.

There may also exist other options unique to each runnable script that make small changes in configuration convinient. See the documentation for each module for more deatils or simply use the `--help` option to get a description of all the available options.

## Modules

### `icarus.abm.parser`

This module parses the ABM data from the source CSV file into a SQL database.

Requirements:

- CSV file of ABM data
- database at `database.db` in config created

Configuration:

| name | purpose | type | deafult |
| - | - | - | - |
| sourcepath | file path of ABM CSV source data  | str | /home/Shared/source/abm/2018/trips.csv |
| resume | specify whether to resume parsing; assumes that tables already exist and are partially completed | bool | false |
| silent | specify whether to print process progress/steps to console; true means the console be blank | bool | false |
| bin_size | amount of trips to parse at a time | int | 500000 |
| create_idxs | specifies whether or not to create indexes described in config schema | bool | true |
| database.db | name of the database to push the parsed data to | str | abm2018 |

### `icarus.abm.validation`

Requirements:

-

Configuration:

| name | purpose | type | deafult |
| - | - | - | - |


### `icarus.input.parser`

This module parses the ABM SQL database into MATSim plans; this includes APN assignment.

Requirements:

- database at `database.db` in config created
- abm database, trips tables created and populated (see `icarus.abm.parser`)
- network database, residences and commerces tables created and populated (see `icarus.network.parser.road`)
- network database, maz table created and populated (see `icarus.network.parser.maz`)

Configuration:

| name | purpose | type | deafult |
| - | - | - | - |
| resume | specify whether to resume parsing; assumes that tables already exist and are partially completed | bool | false |
| silent | specify whether to print process progress/steps to console; true means the console be blank | bool | false |
| bin_size | amount of households to parse at a time | int | 100000 |
| create_idxs | specifies whether or not to create indexes described in config schema | bool | true |
| seed | specify a seed for the random APN assignment process; used to make APN assignment replicable | int | null |
| modes | list of valid modes; plans using modes not in list will be dropped | [int] | [1] |
| acts | list of valid activities; plans using activities not in list will be dropped | [int] | [] |
| database.abm_db | name of the database with the abm data | str | abm2018 |
| database.db | name of the database to push the parsed data to | str | input |

### `icarus.input.generator`

This module builds a XML plans file from an input plans database.

Requirements:

- input database, agents, routes and activites tables created and populated (see `icarus.input.parser`)

Configuration:

| name | purpose | type | deafult |
| - | - | - | - |
| savepath | file path in which to save the XML plans | str | /home/Shared/matsim/run2/input/plans.xml |
| silent | specify whether to print process progress/steps to console; true means the console be blank | bool | false |
| bin_size | amount of plans to generate at a time | int | 100000 |
| region | series of coordinates defining the region to generate plans; leav empty for full network generation | [[int,int]] | [] |
| database.db | name of the database to parse plans from | str | input |

### `icarus.input.validation`

Requirements:

-

Configuration:

| name | purpose | type | deafult |
| - | - | - | - |


### `icarus.output.plans_parser`

Requirements:

-

Configuration:

| name | purpose | type | deafult |
| - | - | - | - |


### `icarus.output.events_parser`

Requirements:

-

Configuration:

| name | purpose | type | deafult |
| - | - | - | - |


### `icarus.network.road_parser`

Requirements:

-

Configuration:

| name | purpose | type | deafult |
| - | - | - | - |

### `icarus.network.maz_parser`

Requirements:

-

Configuration:

| name | purpose | type | deafult |
| - | - | - | - |

### `icarus.network.daymet_parser`

Requirements:

-

Configuration:

| name | purpose | type | deafult |
| - | - | - | - |

### `icarus.network.parcel_parser`

Requirements:

-

Configuration:

| name | purpose | type | deafult |
| - | - | - | - |
