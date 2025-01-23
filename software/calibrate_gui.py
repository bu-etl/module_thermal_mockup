import sys
import PySide6.QtWidgets as qtw
from PySide6.QtCore import Slot, Qt, Signal
from PySide6.QtGui import QAction
from dataclasses import dataclass, field
from typing import List, Optional
from functools import partial
from datetime import datetime
import numpy as np
import pyqtgraph as pg
from com_port import ComPort
from module import ModuleController, Sensor
import firmware_interface as fw

MOD_NAME = 'TM0'
DISABLED_SENSORS = ['L1', 'L2', 'L3', 'L4', 'E2']
firmware_interface = fw.ThermalMockupV2()

MODULE_WRITE_TIMER = 1500
COM_PORT_TIMER = 500
UPDATE_PLOT_TIMER = 1500

def is_float(string):
    try:
        float(string)
        return True
    except ValueError:
        return False
def convert_adc_to_ohms(adc_values: list[str]) -> np.ndarray[float]:
    nums = np.array([int(str(raw_adc)[:-2],16) for raw_adc in adc_values])
    volts = 2.5 + (nums / 2**15 - 1) * 1.024 * 2.5 / 1
    ohms = 1E3 / (5 / volts - 1)
    return ohms    

@dataclass
class CalibrationData:
    calibration_temperatures: List[float] = field(default_factory=list)
    calibration_times: List[float] = field(default_factory=list)
    calibration_adc_values: List[float] = field(default_factory=list)
    fit_slope: Optional[float] = None
    fit_intercept: Optional[float] = None
    all_times: List[float] = field(default_factory=list)
    all_adc_values: List[float] = field(default_factory=list)

    @property
    def calibration_ohms(self) -> np.ndarray[float]:
        return convert_adc_to_ohms(self.calibration_adc_values)
    
    @property
    def all_ohms(self)-> np.ndarray[float]:
        return convert_adc_to_ohms(self.all_adc_values)

    def to_dict(self):
        return {
            "calibration_temperatures": self.calibration_temperatures,
            "calibration_times": [t.isoformat() for t in self.calibration_times],
            "calibration_adc_values": self.calibration_adc_values,
            "fit_slope": self.fit_slope,
            "fit_intercept": self.fit_intercept,
            "all_times": [t.isoformat() for t in self.all_times],
            "all_adc_values": self.all_adc_values
        }

class CalibWidget(qtw.QWidget):
    def __init__(self):
        super(CalibWidget, self).__init__()
        main_layout = qtw.QVBoxLayout(self)

        # >>  DELETE CALIBRATION ROW BUTTON
        self.delete_temp_btn = qtw.QPushButton('Delete')
        main_layout.addWidget(self.delete_temp_btn, stretch=0)

        # >>  CALIBRATION TABLE
        self.table = qtw.QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(['Sensor','Celcius', 'Time'])
        main_layout.addWidget(self.table, stretch=3)

        # >>  CALIBRATION TEMPERATURE INPUT
        calib_widget = qtw.QWidget()
        calib_input_layout = qtw.QHBoxLayout(calib_widget)

        self.user_temp = qtw.QLineEdit()
        calib_input_layout.addWidget(self.user_temp, stretch=1)

        self.add_temp_btn = qtw.QPushButton('Enter')

        calib_input_layout.addWidget(self.add_temp_btn, stretch=0)
        main_layout.addWidget(calib_widget, stretch=0)

class CalibInput(qtw.QWidget):
    temp_added = Signal()

    def __init__(self, module):
        super(CalibInput, self).__init__()

        self.module = module

        #to check if there is data yet for calibration
        self.have_data_for_calib = False
        
        main_layout = qtw.QHBoxLayout(self)

        self.OhmTempPlot = pg.PlotWidget(title="Ohms Vs Celcius", background="#f5f5f5")
        self.OhmTempPlotLegend = self.OhmTempPlot.addLegend()
        self.OhmTempPlot.showGrid(x=True, y=True)
        self.OhmTempPlot.setLabel('left', 'Resistance (Ohms)')  # Y-axis label
        self.OhmTempPlot.setLabel('bottom', f'Celcius ({u"\N{DEGREE SIGN}"}C)')  # X-axis label
        self.ohm_temp_plots = {}
        for sensor in self.module.sensors:
            self.ohm_temp_plots[sensor.name] = self.OhmTempPlot.plot(
                [], [], 
                #pen=self.module.color_map[channel], 
                name=sensor.name,
                symbol="+",
                symbolBrush=self.module.color_map[sensor.name]
            )

        main_layout.addWidget(self.OhmTempPlot, stretch=1)
        
        self.calib_widget = CalibWidget()
        main_layout.addWidget(self.calib_widget, stretch=0)

        self.calib_widget.delete_temp_btn.clicked.connect(self.delete_selected_row)
        self.calib_widget.add_temp_btn.clicked.connect(self.update_data)

        # >>  self Signals
        self.temp_added.connect(self.update_table)
        self.temp_added.connect(self.update_temp_ohm_plot)

    @Slot()
    def update_data(self):
        #add check if module has data yet
        self.have_data_for_calib = all([sensor.calib_data.all_adc_values for sensor in self.module.sensors])
        if (T := self.calib_widget.user_temp.text()) and self.have_data_for_calib and is_float(T):
            for sensor in self.module.sensors:
                sensor.calib_data.calibration_temperatures.append(float(T))
                sensor.calib_data.calibration_adc_values.append(sensor.calib_data.all_adc_values[-1])
                sensor.calib_data.calibration_times.append(sensor.calib_data.all_times[-1])
            self.temp_added.emit()
        elif not self.have_data_for_calib:
            print("All enabled sensors do not have calibration yet. Or temperature could not be converted to float")
            self.calib_widget.user_temp.clear()  
    
    @Slot()
    def update_table(self):
        # Find the next available row in the table
        for sensor in self.module.sensors:
            time = sensor.calib_data.calibration_times[-1]
            temp = sensor.calib_data.calibration_temperatures[-1]

            row_position = self.calib_widget.table.rowCount()
            self.calib_widget.table.insertRow(row_position)

            time_item = qtw.QTableWidgetItem(f"{time.hour}:{str(time.minute).zfill(2)}")
            time_item.setFlags(time_item.flags() & ~Qt.ItemIsEditable)
            self.calib_widget.table.setItem(row_position, 0, qtw.QTableWidgetItem(sensor.name))
            self.calib_widget.table.setItem(row_position, 1, qtw.QTableWidgetItem(str(temp)))
            self.calib_widget.table.setItem(row_position, 2, time_item)

        # Clear the input field
        self.calib_widget.user_temp.clear()   
    
    @Slot()
    def update_temp_ohm_plot(self) -> None:
        for sensor in self.module.sensors:
            self.ohm_temp_plots[sensor.name].setData(
                sensor.calib_data.calibration_temperatures, 
                sensor.calib_data.calibration_ohms
            )

    def delete_selected_row(self):
        # Get the selected row
        selected_row = self.calib_widget.table.currentRow()
        # Remove the selected row if there is a selection
        if selected_row != -1:
            self.calib_widget.table.removeRow(selected_row)


class MainWindow(qtw.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        self.setWindowTitle("Module Calibration") 
        self.module = ModuleController(MOD_NAME, DISABLED_SENSORS, firmware_interface, write_interval=MODULE_WRITE_TIMER)
        for sensor in self.module.sensors:
            sensor.calib_data: CalibrationData = CalibrationData()

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
        self.run_menu.addAction(restart_action)

        download_action = QAction('Download', self)
        download_action.triggered.connect(self.download_data)
        self.run_menu.addAction(download_action)

        upload_db_action = QAction('Upload (DB)', self)
        self.run_menu.addAction(upload_db_action)

        #Port Menu
        self.port_menu = self.menu.addMenu('Port')
        self.com_port= ComPort(readout_interval=COM_PORT_TIMER)

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

        adc_command = firmware_interface.write_sensors(self.module.enabled_sensors)
        self.measure_all_adc = self.write_adc_action('Measure All', adc_command)
        toolbar.addAction(self.measure_all_adc)
        #---------------------------End of Tool Bar-----------------------------#

        #----------------------------Central Layout-----------------------------#
        central_widget = qtw.QWidget()
        main_layout = qtw.QVBoxLayout(central_widget)

        # >> LIVE READOUT BUTTON
        readout_btns = qtw.QWidget()
        readout_btn_layout = qtw.QHBoxLayout(readout_btns)

        self.live_readout_btn = qtw.QPushButton('Start', self)
        self.live_readout_btn.setCheckable(True)
        self.live_readout_btn.toggled.connect(self.module.write_timer)
        self.live_readout_btn.toggled.connect(
            lambda checked: self.live_readout_btn.setText('Start' if not checked else 'Stop')
        )
        readout_btn_layout.addWidget(self.live_readout_btn, stretch=1)

        # >>  SELECT PLOT LINE WIDGET
        self.select_sensor_dropdown = qtw.QComboBox()
        self.select_sensor_dropdown.addItem('Select Sensor')
        for sensor in self.module.sensors:
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
        for sensor in self.module.sensors:
            # Initialize plotItem for each sensor name
            self.ohm_time_plots[sensor.name] = self.OhmTimePlot.plot(
                [], [], #x, y
                pen=self.module.color_map[sensor.name], 
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
        self.com_port.read[str].connect(self.module.read_sensor)
        self.module.read[ModuleController, str, str].connect(self.update_ohm_time_plot)

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
        output_dict = {sensor.name: sensor.calib_data.to_dict() for sensor in self.module.sensors}
        with open(f'./{self.module.name}_{datetime.now()}.json', 'w') as json_file:
            json.dump(output_dict, json_file, indent=4, default=str)
        
    @Slot(int)
    def update_ohm_time_plot(self, module_controller:ModuleController, sensor_name:str, adc_value:str) -> None:
        if module_controller != self.module:
            raise ValueError("Module controller mismatch, something went very wrong.")
        
        sensor = module_controller.sensor(sensor_name)
        # first update data for plot
        sensor.calib_data.all_times.append(datetime.now())
        sensor.calib_data.all_adc_values.append(adc_value)

        # update plot
        if sensor is not None and sensor.calib_data.all_adc_values:
            times = sensor.calib_data.all_times
            t0 = times[0]
            elapsed_time = lambda t: (t - t0).total_seconds() / 60 
            elapsed_times = [elapsed_time(t) for t in times]

            self.ohm_time_plots[sensor_name].setData(
                elapsed_times, sensor.calib_data.all_ohms
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
        for sensor in self.module.sensors:
            temps = np.array(sensor.calib_data.calibration_temperatures)
            ohms = np.array(sensor.calib_data.calibration_ohms)

            #perfom linear fit
            m, b = np.polyfit(temps, ohms, 1)

            #save fit parameters to calib data
            sensor.calib_data.fit_slope = m
            sensor.calib_data.fit_intercept = b

            # Plot the calibration data
            self.calib_fit_plots[sensor.name] = self.calib_input.OhmTempPlot.plot(
                temps, 
                m * temps + b, 
                label=f'Fit: y={m:.2f}x + {b:.2f}',
                pen="black"
            ) 

            # Update the legend
            self.calib_input.ohm_temp_plots[sensor.name].setObjectName(f'{sensor.name}, Fit: y={m:.2f}x + {b:.2f}')
            self.calib_input.OhmTempPlotLegend.removeItem(self.calib_input.ohm_temp_plots[sensor.name])
            self.calib_input.OhmTempPlotLegend.addItem(self.calib_input.ohm_temp_plots[sensor.name], f'{sensor.name}, Fit: y={m:.2f}x + {b:.2f}')

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