from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal, Slot, QTimer
from .sensor import Sensor
from .run_config import ModuleConfig

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

#-----------------OTHER OPTION OF READOUT BUT SEEMS SKETYCH--------------------#

# Module __init__
    # #forward the write signal from the sensors to modules
    # for sensor in self.sensors.values():
    #     # whenever the sensors emit the write signal, 
    #     # the Module will emit its signal to the com port (passes the command along)
    #     sensor.write[str].connect(self._write) # Widget.Signal.connect(Slot)

# Module live_readout:
    # for sensor in self.sensors.values():
    #     sensor.live_readout(start)

# Module _write:
    #self.write.emit(command)

# Com Port _write
    #this delay gives the ADC to catch up with a bunch of consecutive writes?
    #time.sleep(0.2)


