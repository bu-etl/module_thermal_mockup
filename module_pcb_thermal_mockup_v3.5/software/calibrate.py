import sys
from datetime import datetime
import PySide6.QtWidgets as qtw
from PySide6.QtSerialPort import QSerialPort, QSerialPortInfo
from PySide6.QtCore import Signal, Slot, QIODevice, QTextStream
from sqlalchemy import create_engine, select, Engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker
from env import DATABASE_URI
import argparse
import data_models as dm
from typing import Literal
from functools import partial
import pyqtgraph as pg

ENABLED_CHANNELS = [1, 3, 8]
DB_RUN_MODES = ('TEST', 'DEBUG', 'REAL')
DATA_STORE = ['LOCAL', 'DB']

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

class CommPort(qtw.QComboBox):
    log_message = Signal(str)  # Signal to propagate log messages

    def __init__(self, log_callback=None):
        super(CommPort, self).__init__()
        self.port = None
        self.log_callback = log_callback  # Log callback to the main window log method

        self.clear()
        self.addItem('Select Port')
        for port_info in QSerialPortInfo.availablePorts():
            self.addItem(port_info.portName(), port_info)

        #if the dropdown index changes
        self.currentIndexChanged.connect(self.select_port) 

    def select_port(self):
        ''' Signal for when a port is selected from the dropdown'''
        index = self.currentIndex()
        if index > 0:  # Ignoring the first 'Select Port' line
            port_info = self.itemData(index)
            self.connect_port(port_info)

    def connect_port(self, port):
        """Connects and sets port to the corresponding port info"""
        self.disconnect_port() #if already connected to another port, disconnect
        self.log(f"Connecting to port: {port.portName()}")
        self.port = QSerialPort(port)

        self.port.baudRate = QSerialPort.BaudRate.Baud9600
        #self.port.baudRate = QSerialPort.BaudRate.Baud115200
        self.port.breakEnabled = False
        self.port.dataBits = QSerialPort.DataBits.Data8
        self.port.flowControl = QSerialPort.FlowControl.NoFlowControl
        self.port.parity = QSerialPort.Parity.NoParity
        self.port.stopBits = QSerialPort.StopBits.OneStop
        if not self.port.open(QIODevice.ReadWrite):
            print("Failed to open port!")
            self.port = None
            return
        self.port.clear()
        # self.port._error_handler = self.port.errorOccurred.connect(self.log_port_error)

    def read(self) -> None:
        if self.port is None:
            return
        data = self.port.readLine()
        data = QTextStream(data).readAll().strip()
        return data
    
    def write(self, message: str):
        if self.port is None:
            return
        self.com_port.write(message.encode() + b'\n')

    def disconnect_port(self):
        if self.port is not None:
            if hasattr(self.port, '_error_handler'):
                self.port.errorOccurred.disconnect(self.port._error_handler)
            self.port.close()
            self.port = None

    def log(self, message):
        ''' Emit log messages via signal '''
        self.log_message.emit(message)

# #Widget for live readout graph (Not DB Saved)
# class OhmVsTimePlot(pg.PlotWidget):
#     def __init__(self):
#         super(OhmVsTimePlot, self).__init__()

#     def update_plot(self):
#         #update plot
#         pass

# #Widget for each Sensor calib graph (DB Saved)
# class Sensor():
#     def __init__(self, channel: int, com_port: CommPort):
#         #self.run_start_time = None
#         self.channel = channel if channel in ENABLED_CHANNELS else None
#         self.pending_readout = False
#         self.com_port = com_port

#     def readout_adc(self):
#         self.write_port(f'measure {self.channel}')
#         self.pending_readout = True

# class SubassemblyPlot(pg.PlotWidget):
#     def __init__(self):
#         super(SubassemblyPlot, self).__init__()

        #somehow use Sensor to update and put both onto this plot widget, main makes 4 of these

#Main Window
# -> Connect
# -> Temp ref and record button
# -> Make fit button
# -> Finish button

class MainWindow(qtw.QMainWindow):
    log_message = Signal(str)

    def __init__(self):
        super(MainWindow, self).__init__()

        self.setWindowTitle("Module Calibration") 

        self.menu = self.menuBar()
        self.connect_menu = self.menu.addMenu('Connect')

        self.comm_port= CommPort()
        # - What an action is
        #https://www.pythonguis.com/tutorials/pyside6-actions-toolbars-menus/
        # - What QWidgetAction is
        #https://doc.qt.io/qt-6/qwidgetaction.html
        port_widget_action = qtw.QWidgetAction(self)
        port_widget_action.setDefaultWidget(self.comm_port) #set the action for this widget
        self.connect_menu.addAction(port_widget_action)

        central_widget = qtw.QWidget()
        main_layout = qtw.QVBoxLayout(central_widget)

        self.serial_display = qtw.QPlainTextEdit()
        self.serial_display.setReadOnly(True)
        main_layout.addWidget(self.serial_display)

        self.setCentralWidget(central_widget)

        self.comm_port.log_message[str].connect(self.log)
        # layout.addWidget(SubassemblyPlot('Subassembly 1'), 0,0)
        # layout.addWidget(SubassemblyPlot('Subassembly 2'), 0,1)
        # layout.addWidget(SubassemblyPlot('Subassembly 3'), 1,0)
        # layout.addWidget(SubassemblyPlot('Subassembly 4'), 1,1)

        
    @Slot(str)
    def log(self, text: str):
        self.serial_display.appendPlainText(text)

def main():
    APP = qtw.QApplication()

    window = MainWindow()
    window.resize(800, 600)
    window.show()

    sys.exit(APP.exec())

if __name__ == "__main__":
    main()