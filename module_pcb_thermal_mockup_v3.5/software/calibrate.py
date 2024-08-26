import sys
from datetime import datetime
import PySide6.QtWidgets as qtw
from PySide6.QtSerialPort import QSerialPort, QSerialPortInfo
from PySide6.QtCore import Signal, Slot, QIODevice, QTextStream, QTimer
from PySide6.QtGui import QAction
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

class ComPort(qtw.QComboBox):
    log_message = Signal(str)  # Signal to propagate log messages
    data_read_signal = Signal(str) # Signal to propogate to Sensors

    def __init__(self, log_callback=None):
        super(ComPort, self).__init__()
        self.port = None
        self.log_callback = log_callback  # Log callback to the main window log method

        self.clear()
        self.addItem('Select Port')
        for port_info in QSerialPortInfo.availablePorts():
            self.addItem(port_info.portName(), port_info)

        #The Signal of a QComboBox - if current index change 
        self.currentIndexChanged.connect(self.select_port) 

        # Set up continuous reading
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.read)
        self.timer.start(1000)  # Read data every 1000 ms (1 second)

    @Slot() #can be made type safe 
    def select_port(self):
        ''' Slot for when a port is selected from the dropdown'''
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
            self.port = None
            self.log(f"Failed to open port: {port.portName()}")
            return
        self.port.clear()
        self.log(f"Successfully connected to: {port.portName()}")
        # self.port._error_handler = self.port.errorOccurred.connect(self.log_port_error)

    # GOAL: Emit a signal when data is ready
    #make this a signal of ComPort, reading when read it triggers data to be sent to sensors 
    # -> in mainwindow self.ComPort.read.connect(self.ETROC1.whatever) In there you gotta decide if that is data you want
    def read(self) -> None:
        if self.port is None:
            return
        data = self.port.readLine()
        data = QTextStream(data).readAll().strip()

        self.data_read_signal.emit(data) # need to add slot in sensors to read this data, there they deterine if the data is for them
        return data
    
    def write(self, message: str):
        if self.port is None:
            return
        self.com_port.write(message.encode() + b'\n')
    
    def disconnect_port(self):
        if self.port is not None:
            # if hasattr(self.port, '_error_handler'):
            #     self.port.errorOccurred.disconnect(self.port._error_handler)
            self.port.close()
            self.port = None

    def log(self, message):
        ''' Emit log messages via signal '''
        #when a signal is emitted, any widget (slot) connected to it triggers
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
#     def __init__(self, channel: int, com_port: ComPort):
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

class MainWindow(qtw.QMainWindow):
    log_message = Signal(str)

    def __init__(self):
        super(MainWindow, self).__init__()

        self.setWindowTitle("Module Calibration") 

        self.tool_bar = qtw.QToolBar()

        # Create the exit action
        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self._close)
        exit_action.setShortcut('Ctrl+Q')
        self.tool_bar.addAction(exit_action)

        # Set Up Communication Port
        self.com_port= ComPort()
        self.tool_bar.addWidget(self.com_port)
        self.addToolBar(self.tool_bar)

        central_widget = qtw.QWidget()
        main_layout = qtw.QVBoxLayout(central_widget)

        self.serial_display = qtw.QPlainTextEdit()
        self.serial_display.setReadOnly(True)
        main_layout.addWidget(self.serial_display)
        self.setCentralWidget(central_widget)

        self.com_port.log_message[str].connect(self.log)

        # layout.addWidget(SubassemblyPlot('Subassembly 1'), 0,0)
        # layout.addWidget(SubassemblyPlot('Subassembly 2'), 0,1)
        # layout.addWidget(SubassemblyPlot('Subassembly 3'), 1,0)
        # layout.addWidget(SubassemblyPlot('Subassembly 4'), 1,1)
        
    @Slot(str)
    def log(self, text: str):
        self.serial_display.appendPlainText(text)

    @Slot()
    def _close(self):
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