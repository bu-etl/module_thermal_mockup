import sys
import PySide6.QtWidgets as qtw
from PySide6.QtCore import Signal, Slot, QTimer
from PySide6.QtGui import QAction
from sqlalchemy import create_engine, select, Engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker
#from env import DATABASE_URI
#import data_models as dm
from typing import Literal
from functools import partial
import pyqtgraph as pg
from widgets.com_port import ComPort
import re
import time

ENABLED_CHANNELS = [1, 3, 8]
DB_RUN_MODES = ('CALIBRATE')
DATA_STORE = ['DB']

channel_sensor_map = {
    1: 'E3',
    2: 'L1',
    3: 'E1',
    4: 'L2',
    5: 'E2',
    6: 'L3',
    7: 'L4',
    8: 'E4'
}
READOUT_TIME_INTERVAL = 500

from widgets.log_mixin import LogMixin
class Sensor(qtw.QWidget):
    """
    Signals: data_write \n
    Slots: read_adc, write_adc, live_readout
    """
    data_write = Signal(str) # Signal to propogate to Sensors

    def __init__(self, name: str, channel: int):
        super(Sensor, self).__init__()

        self.name = name
        self.channel = channel
        self.measure_adc_command = f"measure {self.channel}"
        self.measurement_pending = False #makes sure the # of reads and # of writes are equal

        # Initialize the data
        self.raw_adcs = []
        self.time = []

    @Slot()
    def live_readout(self, start: bool):
        if start:
            self.timer = QTimer()
            self.timer.timeout.connect(self.write_adc)
            self.timer.start(READOUT_TIME_INTERVAL)  # Update every 1000 ms (1 second)
        elif not start and hasattr(self, 'timer'):
            self.timer.stop()
        else:
            #started live readout before timer
            pass
    @Slot(str)
    def read_adc(self, data:str):
        if self.measure_adc_command in data:
            _, _, raw_adc = data.split()
            self.raw_adcs.append(raw_adc)
            self.measurement_pending = False

    @Slot()
    def write_adc(self):
        if not self.measurement_pending:
            self.data_write.emit(self.measure_adc_command)
            self.measurement_pending = True


class MainWindow(qtw.QMainWindow):
    # log_message = Signal(str)

    def __init__(self):
        super(MainWindow, self).__init__()

        self.setWindowTitle("Module Calibration") 
        #------------------MENU BAR-----------------#
        self.menu = self.menuBar()

        #Run Menu
        self.run_menu = self.menu.addMenu('Run')
        
        # What an action is -> https://www.pythonguis.com/tutorials/pyside6-actions-toolbars-menus/
        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self._close)
        exit_action.setShortcut('Ctrl+Q')
        self.run_menu.addAction(exit_action)

        restart_action = QAction('Restart', self)
        #restart_action.triggered.connnect(self.TODO)
        self.run_menu.addAction(restart_action)

        #Port Menu
        self.port_menu = self.menu.addMenu('Port')
        self.com_port= ComPort()
        # What QWidgetAction is -> https://doc.qt.io/qt-6/qwidgetaction.html
        port_widget_action = qtw.QWidgetAction(self)
        port_widget_action.setDefaultWidget(self.com_port)
        self.port_menu.addAction(port_widget_action)

        port_disconnect_action = QAction('Disconnect', self)
        port_disconnect_action.triggered.connect(self.com_port.disconnect_port)
        self.port_menu.addAction(port_disconnect_action)
        #--------------End of Menu Bar--------------#

        #----------------- Tool Bar ----------------#
        toolbar = self.addToolBar('Main Toolbar')

        self.reset_adc = self.write_adc_action('Reset ADC', 'reset')
        toolbar.addAction(self.reset_adc)

        self.calibrate_adc = self.write_adc_action('Calibrate ADC', 'calibrate')
        toolbar.addAction(self.calibrate_adc)

        adc_command = f"measure {' '.join(map(str, ENABLED_CHANNELS))}"
        self.measure_all_adc = self.write_adc_action('Measure All ADC', adc_command)
        toolbar.addAction(self.measure_all_adc)

        self.probe_adc = self.write_adc_action('Read Probes', 'probe 1 2 3')
        toolbar.addAction(self.probe_adc)
        #-------------End of Tool Bar---------------#

        #--------------Central Layout---------------#
        central_widget = qtw.QWidget()
        main_layout = qtw.QVBoxLayout(central_widget)

        #Sensor Readout
        self.Etroc3 = Sensor('E3', 1)
        # self.Etroc4 = Sensor('E4', 8)

        self.live_readout_btn = qtw.QPushButton('Start', self)
        self.live_readout_btn.setCheckable(True)
        self.live_readout_btn.toggled.connect(self.Etroc3.live_readout)
        #self.live_readout_btn.toggled.connect(self.Etroc4.live_readout)

        self.live_readout_btn.toggled.connect(self.live_readout_btn_text)

        # self.live_readout_btn.toggled.connect(partial(self.toggle_live_readout, self.Etroc3))
        
        main_layout.addWidget(self.live_readout_btn)

        self.serial_display = qtw.QPlainTextEdit()
        self.serial_display.setReadOnly(True)
        main_layout.addWidget(self.serial_display)

        self.setCentralWidget(central_widget)
        #-----------End of Central Layout----------#

        #----------CONNECTING SIGNALS AND SLOTS FOR EXTERNAL WIDGETS------------#
        # REMEMBER:
        # self.Widget.Signal.connect(Slot)
        self.com_port.log_message[str].connect(self.log) 
        self.com_port.data_read[str].connect(self.log)

        #self.Etroc3.log_message[str].connect(self.log)
        self.Etroc3.data_write[str].connect(self.com_port.write)
        #self.Etroc4.data_write[str].connect(self.com_port.write)

        self.com_port.data_read[str].connect(self.Etroc3.read_adc)
        #self.com_port.data_read[str].connect(self.Etroc4.read_adc)

    def write_adc_action(self, name: str, adc_command: str) -> QAction:
        """
        Used for generalizing the adding of toolbar buttons
        """
        write_action = QAction(name, self)
        write_action.triggered.connect(partial(self.com_port.write, adc_command))
        return write_action

    @Slot()
    def live_readout_btn_text(self, checked: bool):
        btn_text = 'Start' if not checked else 'Stop'
        self.live_readout_btn.setText(btn_text)

    @Slot(str)
    def log(self, text: str) -> None:
        self.serial_display.appendPlainText(text)

    @Slot()
    def _close(self) -> None:
        self.com_port.disconnect_port()
        self.close()

def main():
    APP = qtw.QApplication()

    window = MainWindow()
    window.resize(800, 600)
    window.show()

    sys.exit(APP.exec())

if __name__ == "__main__":
    main()