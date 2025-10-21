# Software Information

Author: Hayden Swanson

> *WARNING:* This version of the software will be depreciated soon. New software will be hosted on [Tamalero](https://gitlab.cern.ch/cms-etl-electronics/module_test_sw)

## Run Config
For each run you have to specify a config file in the [TOML format](https://toml.io/en/). 
* keys are case insensitive
* Cannot mix keys between the New Run example 1 and the Adding to Old Run exmaple 2. 

#### Example 1: New Run
```
[RUN]
#reuse_run_id = 4
MODE = "DEBUG"
COLD_PLATE = "Pretty Double Loop Solder Plate"
COMMENT = "debugging software, with old thermal mockup"

[MICROCONTROLLER]
firmware_version = "Thermal Mockup V2"
port = "ttyACM0"

[[MODULES]]
serial_number = "TM0001"
cold_plate_position = 3
orientation = "UP"
disabled_sensors = ['E2', 'L1', 'L2', 'L3', 'L4']
```

#### Example 1: Reuse Run
```
[RUN]
#run = 18
MODE = "DEBUG"
COLD_PLATE = "Pretty Double Loop Solder Plate"
COMMENT = "checking refactor for software!"

[MICROCONTROLLER]
firmware_version = "Thermal Mockup V2"
port = "ttyACM0"

[[MODULES]]
module = "TM0001"
cold_plate_position = 3
orientation = "UP"
disabled_sensors = ['E1', 'E2', 'L1', 'L2', 'L3', 'L4']
#control_board = "ControlBoardName"
#control_board_position = "A"
```
