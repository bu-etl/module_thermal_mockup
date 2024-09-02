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
from widgets.module import Module

#ENABLED_CHANNELS = [1, 3, 8]
ENABLED_CHANNELS = [1, 2, 3, 4, 5, 6, 7, 8]

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
        self.com_port= ComPort(1000)
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
        #adc_command = "measure 8"
        self.measure_all_adc = self.write_adc_action('Measure All ADC', adc_command)
        toolbar.addAction(self.measure_all_adc)

        self.probe_adc = self.write_adc_action('Read Probes', 'probe 1 2 3')
        toolbar.addAction(self.probe_adc)
        #-------------End of Tool Bar---------------#

        #--------------Central Layout---------------#
        central_widget = qtw.QWidget()
        main_layout = qtw.QVBoxLayout(central_widget)

        #Sensor Readout
        self.Module = Module('Module 1', ENABLED_CHANNELS)

        self.live_readout_btn = qtw.QPushButton('Start', self)
        self.live_readout_btn.setCheckable(True)
        self.live_readout_btn.toggled.connect(self.Module.live_readout)
        #self.live_readout_btn.toggled.connect(self.live_readout_btn_text)
        self.live_readout_btn.toggled.connect(
            lambda checked: self.live_readout_btn.setText('Start' if not checked else 'Stop')
        )

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
        self.com_port.read[str].connect(self.log)

        self.Module.write[str].connect(self.com_port._write)
        self.com_port.read[str].connect(self.Module._read)

    def write_adc_action(self, name: str, adc_command: str) -> QAction:
        """
        Used for generalizing the adding of toolbar buttons
        """
        write_action = QAction(name, self)
        write_action.triggered.connect(partial(self.com_port._write, adc_command))
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