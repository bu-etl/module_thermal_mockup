import sys
import PySide6.QtWidgets as qtw
from PySide6.QtCore import Signal, Slot
from PySide6.QtGui import QAction
from sqlalchemy import create_engine, select, Engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker
#from env import DATABASE_URI
#import data_models as dm
from typing import Literal
from functools import partial
import pyqtgraph as pg
from widgets.com_port import ComPort

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

        #------------------MENU BAR-----------------#
        self.menu = self.menuBar()

        #Run Menu
        self.run_menu = self.menu.addMenu('Run')

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
        # What an action is     -> https://www.pythonguis.com/tutorials/pyside6-actions-toolbars-menus/
        # What QWidgetAction is -> https://doc.qt.io/qt-6/qwidgetaction.html
        port_widget_action = qtw.QWidgetAction(self)
        port_widget_action.setDefaultWidget(self.com_port)
        self.port_menu.addAction(port_widget_action)

        #--------------End of Menu Bar--------------#

        #--------------Central Layout---------------#

        central_widget = qtw.QWidget()
        main_layout = qtw.QVBoxLayout(central_widget)

        self.serial_display = qtw.QPlainTextEdit()
        self.serial_display.setReadOnly(True)
        main_layout.addWidget(self.serial_display)
        self.setCentralWidget(central_widget)

        #----------CONNECTING SIGNALS AND SLOTS------------#
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