# Control Board

Old Codimd referance: [Documentation](https://codimd.web.cern.ch/QkczGsSpTheHelzOmx9pmw?view)

> *WARNING:* This PCB design and firmware will be depreciated soon. There will no longer be a need to use a control board as the new Thermal Mockup PCB can connect to the Readout Board therefore the firmware/software used for readout will be the the latest ETL Test stand [firmware](https://gitlab.cern.ch/cms-etl-electronics/module_test_fw) and [software](https://gitlab.cern.ch/cms-etl-electronics/module_test_sw)

## Description
The Control Board is meant to control up to 4 Thermal Mockup Boards at the same time. The board is an arduino uno shield that provides SPI communication connection to all 4 Thermal Mockup(TM) Boards and contains solid state relays to control heater power on the Thermal Mockups. Furthermore it provides an aditonal ADC IC to readout the current that is being sent out on each heater coil.

## Firmware
The Control Board firmware allows for a single microcontroller to connect, communicate, and control up to 4 TM simulataneously. Additional features include power control over pcb heaters and current consumption readout for each TM board. [Latest Control Board Firmware](https://github.com/bu-etl/module_pcb_thermal_mockup/tree/main/control-board/firmware)

### Manual
#### Uplaod Firmware onto Microcontroller board
In order to upload the firmware found in the github above the following is required:
- VS Code with the PlatformIO extension downloaded 
- A microcontrolller such as an Arduino Uno or the Adafruit Metro M4 Express

##### Steps:
1. Download the firmware folder 
2. Open the appropriate folder 
    - In VS Code select project folder PlatformIO should load up and initialize the project
    - *If it is not the first time uploading the frimware you can also choose the folowing:* 
        - open project in VS Code
        OR
        - cd to project directory on terminal

3. Check the code has no errors by building it 
    - On VS Code -> click on the checkmark button on the bottom of the screen (next to the house icon)
    - On terminal -> type command: `pio run`
        - To build project for a specific microcontroller add the `e` flag 
            - e.g: `pio run -e uno` will build project for an arduino uno
4. Find port the micontroller is connected to and modify **platformio.ini** file as necessary 
    - Before connecting the microcontroller to a computer run a command to see connected usb ports
        - On Mac run `ls /dev/tty.*  `
        - On Linux rn `ls /dev/tty* `
    - Connect microcontroller through a USB port to the computer then rerun the previous command you should see a new entry such as:
        - On Mac e.g: `/dev/tty.usbmodem142201`
        - On Linux e.g: `/dev/ttyUSB0`
    - On in the project directory find file **platformio.ini**, change the env variable `monitor_port` to have 
5. Uplaod code to desired microcontroller
    - On VS Code -> click on the arrow on the bottom of the screen (next to the checkmark)
    - On terminal -> type command: `pio run --target upload` (This will try to upload firmare to all microcontrollers listed in the **platformio.ini** file)
        - To upload project to specific microcontroller use previous command to specify build and then append `-t upload` 
            - e.g: `pio run -e uno -t upload` will upload to an arduino uno

Note: Check out [documents for PlatformIO](https://docs.platformio.org/en/latest/core/quickstart.html) for more specfic building and uploading details 

#### Communication via Serial Monitor
Communicaiton between the microcontroller board and user happens through a serial port and can be viewed on a serial monitor.

### Commands
All commands follow the basic structure of a Linux command:
```bash
command -[flags] [arguments]
```

The command is the name of the action you desire to run. Arguments are values passed to the action you desire to run. There can be multiple arguments, all seperated by a space. **If you are using the Control board, in order to specify which of the 4 TM you would like to communicate with, the flag is used** Flags start with `-` and each flag option is one letter. Multiple flags can be passed in the same command (e.g. `-adc`). The mapping of flags to TM number on the control baord is as follows:

| Flag | TM num |
| ---- | ------ |
| a    | 1      |
| b    | 2      |
| c    | 3      |
| d    | 4      |

If a command is run with no flags the default behavior is the action will run on ALL TM. Flags can be in any order, however the order will correspond to the sequence the command is run (e.g `reset -ca` will reset TM baord 3 first then TM board 1).
 
##### Reset:
Cycles reset pin on the AD77x8 on specified TM ADC for 100 microseconds. 
- If no flag is specified, command will cycle through all 4 TM to reset their ADC.
```
reset -[board(s)]
```
If arguments are passed they will be ignored (e.g: `reset -b 23` == `reset -b` ).

##### Calibrate:
Calibrates specified ADC channel(s) of the AD77x8 on specific TM doing the following:
* Writes to the ADC control register to set the channel and its input range 
* Perform zero calibration scaling
* Perform full-scale calibration

```
calibrate -[board(s)] [channel(s)]
```

- If no flag is passed control board will cycle and calibrate specified channel(s) on all TM. 
- If no channels are passed then all channels will be cycled. (e.g. `calibrate` will do a full system calibration of all channels)

Multiple channels can be passed as arguments, order will correspond to the sequence the channel is calibrated.

##### Measure:
Read raw ADC data of specificed AD77x8 channel on specific TM. 

```
status -[board(s)] [channel(s)]
```

At least one argument must be passed to specify what channel to measure (e.g: `measure 2`). 
If no flag is passed then the control board read the specified channel on ALL TM. 

##### Status:
Reads and displays the status register of the AD77x8 on specific TM.

```
status -[board(s)] 
```

If no flag is passed then the control board read the status register on ALL TM. If arguments are passed they will be ignored (e.g `status -bc` and `status -bc 3 5 7`  will result in the same behavior of reading the status register on TM board 2 and 3).

**After reset -> expected value of status: 0**

##### Mode:
Reads or writes the mode register of the AD77x8 on specific TM.

```
mode -[board(s)] <hex>
```

- If no flag is passed control board will cycle and read or write on all TM. 
- If there is no argument then the mode register is read (e.g. `mode`).
- If an argument is passed then the mode register will be written to. The argument must be a hex value of size 2 hex characters (e.g. `mode -a 02` writes the value 2 on TM board 1's mode register). **When writing to the mode register a subsequent read is automatically performed to display the mode register value that was written.** 
- If more then one argument is passed all arguments after the first will be ignored (e.g. `mode 0a 2B` while result is the same behavior as `mode 0a`).

Lower case or uppercase hex digits are both accepted.

**After reset -> expected value of mode: 0**

##### Control:
Reads or writes the control register of the AD77x8 on specific TM.

```
control -[board(s)] <hex>
```

- If no flag is passed control board will cycle and read or write on all TM. 
- If there is no argument then the control register is read (e.g. `control`).
- If an argument is passed then the control register will be written to. The argument must be a hex value of size 2 hex characters (e.g. `control -c 05` writes the value 5 on TM board 3's control register). **When writing to the control register a subsequent read is automatically performed to display the control register value that was written.** 
- If more then one argument is passed all arguments after the first will be ignored (e.g. `control -ad 12 4f 7E` while result is the same behavior as `control -ad 12`).

Lower case or uppercase hex digits are both accepted.

**After reset -> expected value of control: 7**

##### I/O Control:
Reads or writes the I/O control register of the AD77x8 on specific TM.

```
iocontrol -[board(s)] <hex>
```

- If no flag is passed control board will cycle and read or write on all TM. 
- If there is no argument then the I/O control register is read (e.g. `iocontrol`).
- If an argument is passed then the I/O control register will be written to. The argument must be a hex value of size 2 hex characters (e.g. `iocontrol -b 12` writes the value 18 on TM board 2's I/O control register). **When writing to the I/O control register a subsequent read is automatically performed to display the I/O control register value that was written.** 
- If more then one argument is passed all arguments after the first will be ignored (e.g. `iocontrol -c 22 3b cE` while result is the same behavior as `iocontrol -c 22`).

Lower case or uppercase hex digits are both accepted.

**After reset -> expected value of io_control: 3**

##### Gain:
Reads and displays the value in the gain register of the AD77x8 on specific TM.

```
gain -[board(s)] 
```

- If no flag is passed then the control board will read the gain register on ALL TM. 
- If arguments are passed they will be ignored (e.g `gain -ad` and `gain -ad 22 bob 7`  will result in the same behavior of reading the gain register on TM board 1 and 4).

**After reset -> expected value of gain(AD7708): 5000ff or gain(AD7718): 500005**

##### Offset:
Reads and displays the value in the offset register of the AD77x8 on specific TM.

```
offset -[board(s)] 
```

- If no flag is passed then the control board will read the offset register on ALL TM. 
- If arguments are passed they will be ignored (e.g `offset` and `offset 42 3 hi`  will result in the same behavior of reading the offset register on all TM boards).

**After reset -> expected value of offset(AD7708): 8000ff or offset(AD7718): 800000**

##### Filter:
Reads or writes the filter register of the AD77x8 on specific TM.

```
filter -[board(s)] <hex>
```

- If no flag is passed control board will cycle and read or write on all TM. 
- If there is no argument then the filter register is read (e.g. `filter -ac`).
- If an argument is passed then the filter register will be written to. The argument must be a hex value of size 2 hex characters (e.g. `filter -d 08` writes the value 8 on TM board 4's filter register). **When writing to the filter register a subsequent read is automatically performed to display the filter register value that was written.** 
- If more then one argument is passed all arguments after the first will be ignored (e.g. `filter 1c jeje 7` while result is the same behavior as `filter 1c`).

Lower case or uppercase hex digits are both accepted.

**After reset -> expected value of filter: 45**

##### ID:
Reads or writes the ID register of the AD77x8 on specific TM.

```
id -[board(s)] <hex>
```

- If no flag is passed control board will cycle and read or write on all TM. 
- If there is no argument then the ID register is read (e.g. `id`).
- If an argument is passed then the ID register will be written to. The argument must be a hex value of size 2 hex characters (e.g. `id -a 03` writes the value 3 on TM board 1's ID register). **When writing to the ID register a subsequent read is automatically performed to display the ID register value that was written.** 
- If more then one argument is passed all arguments after the first will be ignored (e.g. `id 21 boo 3142 489 5` while result is the same behavior as `id 21`).

Lower case or uppercase hex digits are both accepted.

**After reset -> expected value of id(AD7708): 54 or id(AD7718): 43**

##### Probe:
Reads the raw temperature data of the TMP121(s) on specified TM.
```
probe -[board(s)] <TMP121 number(s)>
```

- If no flag is passed control board will cycle and read the specified tmp121(s) on all TM. 
- If there is no argument passed an error will occur (Must specify at least one tmp121 e.g. (`probe 2`))
- In order to readout all temperature probes write `probe 1 2 3`

##### Heater:
Can turn heater of a specfic TM on or off on CBF.

```
heater -[board(s)] <state>
```

The state argument is a string of either "on" or "off" (the string can also contain capitial letters). When no board is specified the default behavior is to turn all heaters into that state.

##### Current:
Reads the raw ADC value that relates to the current of a specifc TM load on the Control Board.

```
current -[baord(s)]
```

- If no board is specified then the command will cycle and read the adc value for all TM. 
- If arguments are provided an error will occur. 


