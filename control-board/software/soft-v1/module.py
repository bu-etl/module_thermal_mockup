from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal, Slot, QTimer
from run_config import ModuleConfig
from datetime import datetime
import numpy as np


class Sensor(QWidget):
    """
    Signals: write \n
    Slots: read, _write, live_readout
    """
    write = Signal(str) # Signal to propogate to Sensors
    read = Signal(str)

    def __init__(self, name: str, firmware_interface):
        super(Sensor, self).__init__()

        self.name = name
        self.firmware_interface = firmware_interface
        self.measure_adc_command = self.firmware_interface.write_sensor(self.name)
        self.measurement_pending = False #makes sure the # of reads and # of writes are equal
        self.raw_adc_length = 6 #length of this string 72a4ff

        #calibration data
        self.calib_data = {
            'temps': [],
            'times': [],
            'ohms': [],
            'raw_adcs': [],
            'fit_slope': None,
            'fit_intercept': None
        }

        # Initialize the data
        self.raw_adcs = []
        self.times = []

        #Store the last readout to check for this case:
        # > meas
        # > ure 1 7250ff
        self.last_readout = ''

    @Slot(str)
    def _read(self, data:str):
        """
        Reads the output from the ADC, form is something like "measure 1 72a4ff"
        """
        #first check if data was split over two lines, sometimes happens
        merged_line_data = self.last_readout + data
        expected_data_length = len(self.measure_adc_command) + self.raw_adc_length + 1 #+1 for the space between "measure 1" and raw_adc, total is 16 
        data_was_split = (
            (merged_line_data).count(self.measure_adc_command)==1 #if data was split, the merged data should only contain the measure_adc_command once
            and 
            merged_line_data.startswith(self.measure_adc_command) #cleans rare case where previous cut off is same length as current cut off
            and
            len(merged_line_data)==expected_data_length #its length should also be something like len("measure 1 72a4ff"), prevents cases like "measure 1 72a4ffmeasure 2 72a4ff"
        )
        if data_was_split:
            data = merged_line_data
        
        #check if command is in data
        if self.measure_adc_command in data and len(data) == expected_data_length:
            raw_adc = self.firmware_interface.read_sensor(data)
            if raw_adc != '0' or not raw_adc:
                #sometimes raw_adc can give 0, skip append for these
                self.raw_adcs.append(raw_adc)
                self.times.append(datetime.now())
            self.measurement_pending = False
            
            #for more efficient plot updates
            self.read.emit(self.name)
        #for checking split lines on arduino
        self.last_readout = data

    @Slot()
    def _write(self):
        """
        Writes to the ADC, using commands understood by the firmware.
        """
        if not self.measurement_pending:
            self.write.emit(self.measure_adc_command)
            self.measurement_pending = True

    @property
    def ohms(self) -> np.ndarray[float]:
        #last two in raw_adc string always ff
        nums = np.array([int(str(raw_adc)[:-2],16) for raw_adc in self.raw_adcs])
        volts = 2.5 + (nums / 2**15 - 1) * 1.024 * 2.5 / 1
        ohms = 1E3 / (5 / volts - 1)
        return ohms
    
    def temps(self):
        pass

    def __repr__(self):
        return f"Sensor(name={self.name!r})"


class Module(QWidget):
    """
    Signals: write \n
    Slots: read, _write, live_readout
    """
    write = Signal(str) # Signal to propogate to Sensors
    read = Signal(str)

    def __init__(self, module_config:ModuleConfig, enabled_sensors: list[str], firmware_interface, readout_interval=1000):
        super(Module, self).__init__()

        self.module_config = module_config

        self.name = self.module_config.serial_number

        self.enabled_sensors = enabled_sensors # E1, E2, ...
        self.readout_interval = readout_interval
        self.firmware_interface = firmware_interface

        self.color_map = {
            "E3": "#9e0202", #dark red
            "L1": "#00ff00", #lime green
            "E1": "#006400", #dark green
            "L2": "#1e90ff", #dodger blue
            "E2": "#191970", #midnightblue
            "L3": "#ff385d", #salmon red pink
            "L4": "#ffd700", #gold
            "E4": "#a39b00"  #mustard yellow
        }

        self.sensors = [Sensor(sensor_name, firmware_interface) for sensor_name in enabled_sensors]

        self.emit_read = lambda sensor_name: self.read.emit(sensor_name)
        for sensor in self.sensors:
            # whenever the sensors emit the write signal, 
            # the Module will emit its signal to the com port (passes the command along)
            sensor.read[str].connect(self.emit_read) # Widget.Signal.connect(Slot)

    @Slot()
    def live_readout(self, start: bool):
        if start:
            self.timer = QTimer()
            self.timer.timeout.connect(self._write)
            self.timer.start(self.readout_interval)  # Update every X ms
        elif not start and hasattr(self, 'timer'):
            self.timer.stop()

    @Slot(str)
    def _read(self, data:str):
        # when com port reads, trigger read for all 8 sensors, 
        #   -> each sensor has logic to know if the data is for that sensor or not
        for sensor in self.sensors:
            sensor._read(data)

    @Slot()
    def _write(self):
        #manually write depending on number of channels
        if all([not sensor.measurement_pending for sensor in self.sensors]):
            # the emit is the data that gets sent to the com port
            self.write.emit(
                self.firmware_interface.write_sensors(self.enabled_sensors)
            )
            #update the status of the sensors so that they cannot be written to again until data has been read
            for sensor in self.sensors:
                sensor.measurement_pending = True

    def sensor(self, sensor_name) -> Sensor:
        for sensor in self.sensors:
            if sensor.name == sensor_name:
                return sensor

