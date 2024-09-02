from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal, Slot, QTimer
from datetime import datetime

class Sensor(QWidget):
    """
    Signals: write \n
    Slots: read, _write, live_readout
    """
    write = Signal(str) # Signal to propogate to Sensors

    def __init__(self, name: str, channel: int):
        super(Sensor, self).__init__()

        self.name = name
        self.channel = channel
        self.measure_adc_command = f"measure {self.channel}"
        self.measurement_pending = False #makes sure the # of reads and # of writes are equal
        self.raw_adc_length = 6

        # Initialize the data
        self.raw_adcs = []
        self.times = []

        #Store the last readout to check for this case:
        # > meas
        # > ure 1 7250ff
        self.last_readout = ''

    @Slot()
    def live_readout(self, start: bool):
        if start:
            self.timer = QTimer()
            self.timer.timeout.connect(self._write)
            self.timer.start(1000)  # Update every 1000 ms (1 second)
        elif not start and hasattr(self, 'timer'):
            self.timer.stop()
        else:
            #started live readout before timer
            pass

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
            len(merged_line_data)==expected_data_length #its length should also be something like len("measure 1 72a4ff"), prevents cases like "measure 1 72a4ffmeasure 2 72a4ff"
        )
        if data_was_split:
            data = merged_line_data
        
        #check if command is in data
        if self.measure_adc_command in data:
            raw_adc = data.split()[-1] #last one will always be raw_adc
            self.raw_adcs.append(raw_adc)
            self.times.append(datetime.now())
            self.measurement_pending = False
        
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