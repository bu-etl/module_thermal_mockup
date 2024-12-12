import sys
import PySide6.QtWidgets as qtw
from PySide6.QtCore import Slot, Qt, Signal
from PySide6.QtGui import QAction
from sqlalchemy import create_engine, select, Engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker
#from env import DATABASE_URI
#import data_models as dm
from functools import partial
from datetime import datetime
import numpy as np

import pyqtgraph as pg
from widgets.com_port import ComPort
from widgets.module import Module
from widgets.calib_input import CalibInput

ENABLED_CHANNELS = [1, 2,3,5,6,8]
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
    def __init__(self):
        super(MainWindow, self).__init__()

        self.setWindowTitle("Module Calibration") 
        #--------------------------------MENU BAR-------------------------------#
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

        download_action = QAction('Download', self)
        download_action.triggered.connect(self.download_data)
        self.run_menu.addAction(download_action)

        upload_db_action = QAction('Upload (DB)', self)
        self.run_menu.addAction(upload_db_action)

        #Port Menu
        self.port_menu = self.menu.addMenu('Port')
        self.com_port= ComPort(readout_interval=500)

        # What QWidgetAction is -> https://doc.qt.io/qt-6/qwidgetaction.html
        port_widget_action = qtw.QWidgetAction(self)
        port_widget_action.setDefaultWidget(self.com_port)
        self.port_menu.addAction(port_widget_action)

        port_disconnect_action = QAction('Disconnect', self)
        port_disconnect_action.triggered.connect(self.com_port.disconnect_port)
        self.port_menu.addAction(port_disconnect_action)
        #----------------------------End of Menu Bar----------------------------#

        #------------------------------- Tool Bar ------------------------------#
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
        #---------------------------End of Tool Bar-----------------------------#

        #----------------------------Central Layout-----------------------------#
        central_widget = qtw.QWidget()
        main_layout = qtw.QVBoxLayout(central_widget)

        # >> LIVE READOUT BUTTON
        self.module = Module('TM0001', ENABLED_CHANNELS, readout_interval=1)

        readout_btns = qtw.QWidget()
        readout_btn_layout = qtw.QHBoxLayout(readout_btns)

        self.live_readout_btn = qtw.QPushButton('Start', self)
        self.live_readout_btn.setCheckable(True)
        self.live_readout_btn.toggled.connect(self.module.live_readout)
        self.live_readout_btn.toggled.connect(
            lambda checked: self.live_readout_btn.setText('Start' if not checked else 'Stop')
        )
        readout_btn_layout.addWidget(self.live_readout_btn, stretch=1)

        # >>  SELECT PLOT LINE WIDGET
        self.select_sensor_dropdown = qtw.QComboBox()
        self.select_sensor_dropdown.addItem('Select Sensor')
        for channel, sensor in self.module.sensors.items():
            self.select_sensor_dropdown.addItem(
                sensor.name, sensor
            )

        readout_btn_layout.addWidget(self.select_sensor_dropdown, stretch=0)
        main_layout.addWidget(readout_btns)

        # >>  OHM VS TIME PLOT
        readout_info = qtw.QWidget()
        readout_info_layout = qtw.QHBoxLayout(readout_info)

        self.OhmTimePlot = pg.PlotWidget(title="Ohms Over Time", background="#f5f5f5")
        self.OhmTimePlot.addLegend()
        self.OhmTimePlot.showGrid(x=True, y=True)
        self.OhmTimePlot.setLabel('left', 'Resistance (Ohms)')  # Y-axis label
        self.OhmTimePlot.setLabel('bottom', 'Time (s)')  # X-axis label
        self.ohm_time_plots = {}
        for channel, sensor in self.module.sensors.items():
            # Initialize plotItem for each sensor name
            self.ohm_time_plots[channel] = self.OhmTimePlot.plot(
                [], [], #x, y
                pen=self.module.color_map[channel], 
                name=sensor.name
            )
        readout_info_layout.addWidget(self.OhmTimePlot, stretch=1)

        # >>  SERIAL MONITOR
        self.serial_display = qtw.QPlainTextEdit()
        self.serial_display.setReadOnly(True)
        readout_info_layout.addWidget(self.serial_display, stretch=0)

        main_layout.addWidget(readout_info)

        # >>  CALIBRATION INPUT/OUTPUT and Display
        self.calib_input = CalibInput(self.module)
        main_layout.addWidget(self.calib_input)

        # >> Fitting
        self.fit_data_btn = qtw.QPushButton('Linear Fit')
        self.fit_data_btn.clicked.connect(self.linear_calib_fit)
        main_layout.addWidget(self.fit_data_btn)

        # MAIN WINDOW CONNECTIONS
        self.select_sensor_dropdown.currentIndexChanged.connect(
            partial(self.select_sensor, self.OhmTimePlot, self.ohm_time_plots)
        )
        self.select_sensor_dropdown.currentIndexChanged.connect(
            partial(self.select_sensor, self.calib_input.OhmTempPlot, self.calib_input.ohm_temp_plots)
        )

        self.setCentralWidget(central_widget)
        #-------------------------End of Central Layout------------------------#

        #----------CONNECTING SIGNALS AND SLOTS FOR EXTERNAL WIDGETS------------#
        # REMEMBER: Widget.Signal.connect(Slot)
        self.com_port.log_message[str].connect(self.log) 
        self.com_port.read[str].connect(self.log)

        self.module.write[str].connect(self.com_port._write)
        self.com_port.read[str].connect(self.module._read)
        #self.com_port.read[str].connect(self.update_ohm_time_plot)
        self.module.read[int].connect(self.update_ohm_time_plot)

    def write_adc_action(self, name: str, adc_command: str) -> QAction:
        """
        Used for generalizing the adding of toolbar buttons
        """
        write_action = QAction(name, self)
        write_action.triggered.connect(partial(self.com_port._write, adc_command))
        return write_action
    
    @Slot()
    def download_data(self):
        import json
        #loop through sensors and make sensor calib data
        output_dict = {
            sensor.name: {
                **sensor.calib_data,
                "all_raw_adcs": sensor.raw_adcs, 
                "all_times": sensor.times
            } 
            for sensor in self.module.sensors.values()
        }
        with open(f'./calibration_data_{self.module.name}_{datetime.now()}.json', 'w') as json_file:
            json.dump(output_dict, json_file, indent=4, default=str)
        
    @Slot(int)
    def update_ohm_time_plot(self, channel: int) -> None:
        sensor = self.module.sensors.get(channel)
        if sensor is not None and sensor.raw_adcs:
            t0 = sensor.times[0]
            elapsed_time = lambda t: (t - t0).total_seconds() / 60 
            elapsed_times = [elapsed_time(t) for t in sensor.times]

            self.ohm_time_plots[channel].setData(
                elapsed_times, sensor.ohms
            )

    @Slot(int)
    def select_sensor(self, plot_widget, plots: dict, index: int) -> None:
        for live_plot in plots.values():
            plot_widget.removeItem(live_plot)       
        if index <= 0:
            #select all sensors
            for live_plot in plots.values():
               plot_widget.addItem(live_plot)
        elif index > 0:
            #select singular sensor
            sensor_name = self.select_sensor_dropdown.currentText()
            channel = self.module.get_channel(sensor_name)
            plot_widget.addItem(plots[channel])

    @Slot()
    def linear_calib_fit(self):
        #get all the calib data
        self.calib_fit_plots = {}
        for channel, sensor in self.module.sensors.items():
            temps = np.array(sensor.calib_data['temps'])
            ohms = np.array(sensor.calib_data['ohms'])

            #perfom linear fit
            m, b = np.polyfit(temps, ohms, 1)

            #save fit parameters to calib data
            sensor.calib_data['fit_slope'] = m
            sensor.calib_data['fit_intercept'] = b

            # Plot the calibration data
            self.calib_fit_plots[channel] = self.calib_input.OhmTempPlot.plot(
                temps, 
                m * temps + b, 
                label=f'Fit: y={m:.2f}x + {b:.2f}',
                pen="black"
            ) 

            # Update the legend
            self.calib_input.ohm_temp_plots[channel].setObjectName(f'{sensor.name}, Fit: y={m:.2f}x + {b:.2f}')
            self.calib_input.OhmTempPlotLegend.removeItem(self.calib_input.ohm_temp_plots[channel])
            self.calib_input.OhmTempPlotLegend.addItem(self.calib_input.ohm_temp_plots[channel], f'{sensor.name}, Fit: y={m:.2f}x + {b:.2f}')

    @Slot()
    def live_readout_btn_text(self, checked: bool) -> None:
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