from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal, Slot, QTimer
from .sensor import Sensor

class Module(QWidget):
    """
    Signals: write \n
    Slots: read, _write, live_readout
    """
    write = Signal(str) # Signal to propogate to Sensors
    read = Signal(int)

    def __init__(self, name: str, enabled_channels: list[int], readout_interval=1000):
        super(Module, self).__init__()
        self.name = name
        self.enabled_channels = enabled_channels
        self.readout_interval = readout_interval

        self.channel_map = {
            1: 'E3',
            2: 'L1',
            3: 'E1',
            4: 'L2',
            5: 'E2',
            6: 'L3',
            7: 'L4',
            8: 'E4'
        }

        self.sensors = {
            channel: Sensor(self.channel_map[channel], channel) for channel in enabled_channels
        }

        self.emit_read = lambda channel: self.read.emit(channel)
        for sensor in self.sensors.values():
            # whenever the sensors emit the write signal, 
            # the Module will emit its signal to the com port (passes the command along)
            sensor.read[int].connect(self.emit_read) # Widget.Signal.connect(Slot)

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
        for sensor in self.sensors.values():
            sensor._read(data)

    @Slot()
    def _write(self):
        #manually write depending on number of channels
        if all([not sensor.measurement_pending for sensor in self.sensors.values()]):
            # the emit is the data that gets sent to the com port
            self.write.emit(f"measure {' '.join(map(str, self.enabled_channels))}")
            #update the status of the sensors so that they cannot be written to again until data has been read
            for sensor in self.sensors.values():
                sensor.measurement_pending = True

    def get_channel(self, search_name: str):
        for channel, name in self.channel_map.items():
            if name == search_name:
                return channel

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


