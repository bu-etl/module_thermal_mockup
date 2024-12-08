import PySide6.QtWidgets as qtw
from PySide6.QtCore import Slot, QTimer
from PySide6.QtGui import QAction
from sqlalchemy import create_engine, select
from sqlalchemy.orm import scoped_session, sessionmaker
from database.env import DATABASE_URI
from database import models as dm
import pyqtgraph as pg
import sys
from run_config import RunConfigModal
from com_port import ComPort
from module import ModuleController
import firmware_interface as fw
from functools import partial
import numpy as np
from datetime import datetime

def find_module(name:str, modules:list[dm.Module]) -> dm.Module:
    for module in modules:
        if module.name == name:
            return module
    return None

class MainWindow(qtw.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Howdy Doody")


        #------------------CREATE DB SESSION---------------------#
        engine = create_engine(DATABASE_URI)
        Session = scoped_session(sessionmaker(bind=engine))
        self.session = Session()
        #--------------------------------------------------------#
        self.module_controllers = []
        #--------------------------------MENU BAR-------------------------------#
        self.menu = self.menuBar()

        #Run Menu
        self.run_menu = self.menu.addMenu('Run')
        
        # What an action is -> https://www.pythonguis.com/tutorials/pyside6-actions-toolbars-menus/
        run_config_action = QAction('Choose Run Config', self)
        run_config_action.triggered.connect(self.configure_from_run_config)
        self.run_menu.addAction(run_config_action)

        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self._close)
        exit_action.setShortcut('Ctrl+Q')
        self.run_menu.addAction(exit_action)

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
        #---------------------------End of Tool Bar-----------------------------#

        central_widget = qtw.QWidget()
        main_layout = qtw.QVBoxLayout(central_widget)

        readout_btns = qtw.QWidget()
        readout_btn_layout = qtw.QHBoxLayout(readout_btns)

        self.live_readout_btn = qtw.QPushButton('Start', self)
        self.live_readout_btn.setCheckable(True)
        self.live_readout_btn.toggled.connect(
            lambda checked: self.live_readout_btn.setText('Start' if not checked else 'Stop')
        )
        readout_btn_layout.addWidget(self.live_readout_btn, stretch=1)

        # >>  SELECT PLOT LINE WIDGET
        self.select_sensor_dropdown = qtw.QComboBox()
        self.select_sensor_dropdown.addItem('Select Sensor')
        readout_btn_layout.addWidget(self.select_sensor_dropdown, stretch=0)

        self.data_select_dropdown = qtw.QComboBox()
        self.data_select_dropdown.addItem('Data Type')
        readout_btn_layout.addWidget(self.data_select_dropdown, stretch=0)
        self.data_select_dropdown.addItem(
            "volts", "volts"
        )    
        self.data_select_dropdown.addItem(
            "ohms", "ohms"
        )
        self.data_select_dropdown.addItem(
            "celcius", "celcius"
        )

        self.data_select_dropdown.setCurrentIndex(1)

        main_layout.addWidget(readout_btns)

        readout_info = qtw.QWidget()
        readout_info_layout = qtw.QHBoxLayout(readout_info)

        self.SensorDataTimePlot = pg.PlotWidget(title="Sensor Data Over Time", background="#f5f5f5")
        self.SensorDataTimePlot.addLegend()
        self.SensorDataTimePlot.showGrid(x=True, y=True)
        self.SensorDataTimePlot.setLabel('left', 'Data')  # Y-axis label
        self.SensorDataTimePlot.setLabel('bottom', 'Minutes')  # X-axis label
        self.sensor_data_time_plots = {}

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(5000)  # Update every X ms

        readout_info_layout.addWidget(self.SensorDataTimePlot, stretch=1)

        self.serial_display = qtw.QPlainTextEdit()
        self.serial_display.setReadOnly(True)
        readout_info_layout.addWidget(self.serial_display, stretch=0)

        main_layout.addWidget(readout_info)

        self.setCentralWidget(central_widget)

        self.com_port.log_message[str].connect(self.log) 
        self.com_port.read[str].connect(self.log)

        self.select_sensor_dropdown.currentIndexChanged.connect(
            partial(self.select_sensor, self.SensorDataTimePlot, self.sensor_data_time_plots)
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
            module_sensor_name = self.select_sensor_dropdown.currentText()
            plot_widget.addItem(plots[module_sensor_name])

    def write_adc_action(self, name: str, adc_command: str) -> QAction:
        """
        Used for generalizing the adding of toolbar buttons
        """
        write_action = QAction(name, self)
        write_action.triggered.connect(partial(self.com_port._write, adc_command))
        return write_action

    @Slot()
    def configure_from_run_config(self):
        """
        This method is the master method for adding all the information form
        the run configuration
        """
        self.run_config_modal = RunConfigModal(self.session)

        if self.run_config_modal.exec():
            self.com_port.connect_by_name(self.run_config_modal.run_config.microcontroller.port)
            
            self.run_config = self.run_config_modal.run_config
            if len(self.run_config.modules) != 1:
                raise NotImplementedError("multi modules is not implemented yet")
            
            for mod_config in self.run_config.modules:
                firmware_name = self.run_config.microcontroller.firmware_version

                db_data = self.run_config_modal.db_data
                module_controller = ModuleController(
                    mod_config, 
                    fw.firmware_select(firmware_name), 
                    readout_interval=1000
                )
                module_controller.module = find_module(mod_config.serial_number, db_data["modules"])
                module_controller.run = db_data["run"]
                module_controller.control_board = db_data["control_board"]
                module_controller.control_board_position = mod_config.control_board_position

                self.live_readout_btn.toggled.connect(module_controller.live_readout)
                for sensor in module_controller.sensors:
                    self.select_sensor_dropdown.addItem(f"{module_controller.name}_{sensor.name}", sensor)
                    # Initialize plotItem for each sensor name
                    self.sensor_data_time_plots[f"{module_controller.name}_{sensor.name}"] = self.SensorDataTimePlot.plot(
                        [], [], #x, y
                        pen=module_controller.color_map[sensor.name], 
                        name=f"{module_controller.name}_{sensor.name}"
                    )
                module_controller.write[str].connect(self.com_port._write)
                self.com_port.read[str].connect(module_controller.read_sensor)
                module_controller.read[ModuleController, str, str].connect(self.save_data)
                
                self.module_controllers.append(module_controller)
            self.session.commit() # this is for any new runs that have been added to the session

        else:
            # remove all data and reset the page if there is any
            # if theres not do nothing!
            print("Cancel!")

    def save_data(self, module_controller:ModuleController, sensor_name:str, raw_adc:str):
        db_data = self.run_config_modal.db_data
        run_config = self.run_config_modal.run_config

        if db_data is not None and run_config is not None:
            data = dm.Data(
                run = module_controller.run,
                control_board = module_controller.control_board,
                control_board_position = module_controller.control_board_position,
                module = module_controller.module,
                module_orientation = module_controller.config.orientation,
                plate_position = module_controller.config.cold_plate_position,
                sensor = sensor_name,
                timestamp = datetime.now(),
                raw_adc = raw_adc
            )

            self.session.add(data)
            self.session.commit()

    # NEED THIS TO TRIGGER EVERY 3 or so seconds and read from db
    @Slot(int)
    def update_plot(self) -> None:
        if not hasattr(self, "run_config_modal"):
            return
        if not hasattr(self.run_config_modal, 'db_data'):
            return
        for mod_controller in self.module_controllers:
            for sensor in mod_controller.enabled_sensors:
                module = mod_controller.module
                query = select(dm.Data).where(
                    dm.Data.run==mod_controller.run, 
                    dm.Data.sensor==sensor, 
                    dm.Data.module == module
                )

                data = self.session.execute(query).scalars().all()
                if not data:
                    return
                
                t0 = data[0].timestamp
                elapsed_time = lambda t: (t - t0).total_seconds() / 60 
                elapsed_times = [elapsed_time(d.timestamp) for d in data]

                if self.data_select_dropdown.currentData() == "volts":
                    y_data = [d.volts for d in data]
                elif self.data_select_dropdown.currentData() == "ohms":
                    y_data = [d.ohms for d in data]
                elif self.data_select_dropdown.currentData() == "celcius":
                     y_data = [d.celcius for d in data if d.celcius is not None]              
                else:
                    elapsed_times = []
                    y_data = []             

                self.sensor_data_time_plots[f"{mod_controller.name}_{sensor}"].setData(
                    elapsed_times, y_data
                )
        
    @Slot(str)
    def log(self, text: str) -> None:
        self.serial_display.appendPlainText(text)

    @Slot()
    def _close(self) -> None:
        print("disconnected")
        self.session.close_all()
        self.com_port.disconnect_port()
        self.close()

if __name__ == "__main__":
    app = qtw.QApplication()

    window = MainWindow()
    window.resize(800, 800)
    window.show()

    sys.exit(app.exec())

    print("disconnecting")
    window.session.close()