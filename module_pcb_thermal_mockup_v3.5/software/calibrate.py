import sys
import csv
from collections import deque
from datetime import datetime
import PySide6.QtWidgets as qtw
import PySide6.QtCharts as qtc
from PySide6.QtSerialPort import QSerialPort, QSerialPortInfo
from PySide6 import QtCore
from PySide6.QtCore import Qt
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

#options:
#keep communication and everything together
#split it up by sensor

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

class Port:
    def __init__(self):
        self.port = None
        #self.all_ports = QSerialPortInfo.availablePorts() # make this go elsewhere

        #add all_ports as options to the port layout
        #set up action that when selected it makes self.port port info

    def connect(self, port):
        self.disconnect()
        self.log(f"Connecting to port: {port.portName()}")
        self.port = QSerialPort(port)
        self.port.baudRate = QSerialPort.BaudRate.Baud9600
        #self.port.baudRate = QSerialPort.BaudRate.Baud115200
        self.port.breakEnabled = False
        self.port.dataBits = QSerialPort.DataBits.Data8
        self.port.flowControl = QSerialPort.FlowControl.NoFlowControl
        self.port.parity = QSerialPort.Parity.NoParity
        self.port.stopBits = QSerialPort.StopBits.OneStop
        if not self.port.open(QtCore.QIODevice.ReadWrite):
            print("Failed to open port!")
            self.port = None
            return
        self.port.clear()
        # self.port._error_handler = self.port.errorOccurred.connect(self.log_port_error)

    def read(self) -> None:
        if self.port is None:
            return
        data = self.port.readLine()
        data = QtCore.QTextStream(data).readAll().strip()
        return data
    
    def write(self, message: str):
        if self.port is None:
            return
        self.com_port.write(message.encode() + b'\n')

    def disconnect(self):
        if self.port is not None:
            if hasattr(self.port, '_error_handler'):
                self.port.errorOccurred.disconnect(self.port._error_handler)
            self.port.close()
            self.port = None


#Widget for live readout graph (Not DB Saved)
class OhmVsTimePlot(pg.PlotWidget):
    def __init__(self):
        super(OhmVsTimePlot, self).__init__()

    def update_plot(self):
        #update plot
        pass

#Widget for each Sensor calib graph (DB Saved)
class Sensor():
    def __init__(self, channel: int, com_port):
        #self.run_start_time = None
        self.channel = channel if channel in ENABLED_CHANNELS else None
        self.pending_readout = False
        self.com_port = com_port

    def readout_adc(self):
        self.write_port(f'measure {self.channel}')
        self.pending_readout = True

class SubassemblyPlot(pg.PlotWidget):
    def __init__(self):
        super(SubassemblyPlot, self).__init__()

        #somehow use Sensor to update and put both onto this plot widget, main makes 4 of these

#Main Window
# -> Connect
# -> Temp ref and record button
# -> Make fit button
# -> Finish button

class MainWindow(qtw.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        self.setWindowTitle("Module Calibration") 

        layout = qtw.QGridLayout()

        layout.addWidget(SubassemblyPlot('Subassembly 1'), 0,0)
        layout.addWidget(SubassemblyPlot('Subassembly 2'), 0,1)
        layout.addWidget(SubassemblyPlot('Subassembly 3'), 1,0)
        layout.addWidget(SubassemblyPlot('Subassembly 4'), 1,1)

        self.setCentralWidget(layout)


