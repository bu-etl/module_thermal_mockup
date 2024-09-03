import sys
import PySide6.QtWidgets as qtw
from PySide6.QtCore import Slot
from PySide6.QtGui import QAction
from sqlalchemy import create_engine, select, Engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker
#from env import DATABASE_URI
#import data_models as dm
from functools import partial
import pyqtgraph as pg
from widgets.com_port import ComPort
from widgets.module import Module

ENABLED_CHANNELS = [1, 3, 8]
#ENABLED_CHANNELS = [1, 2, 3, 4, 5, 6, 7, 8]
DB_RUN_MODES = ('CALIBRATE')
DATA_STORE = ['DB']

channel_equations = {
    1: lambda ohms: (ohms - 723.5081039009991) / 3.0341696569667955,
    3: lambda ohms: (ohms - 740.9934812257274) / 3.6682463501270317,
    7: lambda ohms: (ohms - 843.5650697047028) / 3.5332573008093036,
    8: lambda ohms: (ohms - 735.6945560895681) / 3.0846916504139346,
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
        self.com_port= ComPort(readout_interval=150)

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

        self.reset_adc = self.write_adc_action('Reset', 'reset')
        toolbar.addAction(self.reset_adc)

        self.calibrate_adc = self.write_adc_action('Calibrate', 'calibrate')
        toolbar.addAction(self.calibrate_adc)

        adc_command = f"measure {' '.join(map(str, ENABLED_CHANNELS))}"
        self.measure_all_adc = self.write_adc_action('Measure All', adc_command)
        toolbar.addAction(self.measure_all_adc)

        self.probe_adc = self.write_adc_action('Probes', 'probe 1 2 3')
        toolbar.addAction(self.probe_adc)
        #-------------End of Tool Bar---------------#

        #--------------Central Layout---------------#
        central_widget = qtw.QWidget()
        main_layout = qtw.QVBoxLayout(central_widget)

        #LIVE READOUT BUTTON
        self.Module = Module('Module 1', ENABLED_CHANNELS, readout_interval=100)

        self.live_readout_btn = qtw.QPushButton('Start', self)
        self.live_readout_btn.setCheckable(True)

        self.live_readout_btn.toggled.connect(self.Module.live_readout)
        self.live_readout_btn.toggled.connect(
            lambda checked: self.live_readout_btn.setText('Start' if not checked else 'Stop')
        )
        main_layout.addWidget(self.live_readout_btn)

        # OHM VS TIME PLOT
        colors = ['r', 'g', 'b', 'c', 'm', 'y', 'w', 'black']
        self.plotWidget = pg.PlotWidget(title="Ohms Over Time", background="#ebf0ee")
        # for i, sensor in enumerate(self.Module.sensors.values()):
        #     self.plotWidget.plot(pen=colors[i], name=sensor.name)
        self.plotWidget.addLegend()
        self.plotWidget.showGrid(x=True, y=True)
        self.live_plots = {}
        for i, (channel, sensor) in enumerate(self.Module.sensors.items()):
            # Initialize plotItem for each sensor name
            self.live_plots[channel] = self.plotWidget.plot([], [], pen=colors[i], name=sensor.name)
        main_layout.addWidget(self.plotWidget)

        # SELECT PLOT LINE WIDGET
        self.select_sensor_dropdown = qtw.QComboBox()
        self.select_sensor_dropdown.addItem('Select Sensor')
        for channel, sensor in self.Module.sensors.items():
            self.select_sensor_dropdown.addItem(
                sensor.name, self.live_plots[channel]
            )
        self.select_sensor_dropdown.currentIndexChanged.connect(self.select_sensor)
        main_layout.addWidget(self.select_sensor_dropdown)

        # SERIAL MONITOR
        self.serial_display = qtw.QPlainTextEdit()
        self.serial_display.setReadOnly(True)
        main_layout.addWidget(self.serial_display)

        self.setCentralWidget(central_widget)
        #-----------End of Central Layout----------#

        #----------CONNECTING SIGNALS AND SLOTS FOR EXTERNAL WIDGETS------------#
        # REMEMBER: Widget.Signal.connect(Slot)
        self.com_port.log_message[str].connect(self.log) 
        self.com_port.read[str].connect(self.log)

        self.Module.write[str].connect(self.com_port._write)
        self.com_port.read[str].connect(self.Module._read)
        #self.com_port.read[str].connect(self.update_plot)
        self.Module.read[int].connect(self.update_plot)

    def write_adc_action(self, name: str, adc_command: str) -> QAction:
        """
        Used for generalizing the adding of toolbar buttons
        """
        write_action = QAction(name, self)
        write_action.triggered.connect(partial(self.com_port._write, adc_command))
        return write_action
    
    def update_plot(self, channel: int):
        sensor = self.Module.sensors.get(channel)
        if sensor is not None and sensor.raw_adcs:
            t0 = sensor.times[0]
            elapsed_time = lambda t: (t - t0).total_seconds() / 60 
            elapsed_times = [elapsed_time(t) for t in sensor.times]

            self.live_plots[channel].setData(
                elapsed_times, sensor.ohms
            )

    @Slot(int)
    def select_sensor(self, index):
        for _, live_plot in self.live_plots.items():
            self.plotWidget.removeItem(live_plot)       
        if index <= 0:
            #select all sensors
            for _, live_plot in self.live_plots.items():
               self.plotWidget.addItem(live_plot)
        elif index > 0:
            #select singular sensor
            sensor_name = self.select_sensor_dropdown.currentText()
            channel = self.Module.get_channel(sensor_name)
            self.plotWidget.addItem(self.live_plots[channel])

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