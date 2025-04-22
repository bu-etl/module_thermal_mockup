import PySide6.QtWidgets as qtw
from PySide6.QtCore import Slot, QTimer, Qt
from PySide6.QtGui import QAction
from sqlalchemy import create_engine, select
from sqlalchemy.orm import scoped_session, sessionmaker
from database.env import DATABASE_URI
from database import models as dm
import pyqtgraph as pg
import sys
from run_config import RunConfigModal, RunConfig, ModuleConfig
from com_port import ComPort
from module import ModuleController
from bump_bond_monitor import BumpBondMonitor
import firmware_interface as fw
from functools import partial
from datetime import datetime

MODULE_WRITE_TIMER = 1500
COM_PORT_TIMER = 500
UPDATE_PLOT_TIMER = 1500

class MainWindow(qtw.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Howdy Doody")

        #------------------CREATE DB SESSION---------------------#
        engine = create_engine(DATABASE_URI)
        Session = scoped_session(sessionmaker(bind=engine))
        self.session = Session()
        #--------------------------------------------------------#
        self.module_controllers: list[ModuleController] = []
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

        no_measurement_pending_action = QAction("no_measurement_pending", self)
        no_measurement_pending_action.triggered.connect(self.no_measurement_pending)
        
        toolbar.addAction(no_measurement_pending_action)
        #---------------------------End of Tool Bar-----------------------------#

        central_widget = qtw.QWidget()
        self.main_layout = qtw.QVBoxLayout(central_widget)

        self.run_banner = qtw.QLabel("No run selected")
        self.run_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.run_banner.setStyleSheet("color: blue; font-size: 16px; font-weight: bold;")
        self.main_layout.addWidget(self.run_banner)

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

        self.main_layout.addWidget(readout_btns)

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
        self.timer.start(UPDATE_PLOT_TIMER)  # Update every X ms

        readout_info_layout.addWidget(self.SensorDataTimePlot, stretch=1)

        self.serial_display = qtw.QPlainTextEdit()
        self.serial_display.setReadOnly(True)
        readout_info_layout.addWidget(self.serial_display, stretch=0)

        self.main_layout.addWidget(readout_info)

        self.setCentralWidget(central_widget)

        self.com_port.log_message[str].connect(self.log) 
        self.com_port.read[str].connect(self.log)

        self.select_sensor_dropdown.currentIndexChanged.connect(
            partial(self.select_sensor, self.SensorDataTimePlot, self.sensor_data_time_plots)
        )

        self.run_note = qtw.QWidget()
        run_note_layout = qtw.QHBoxLayout()
        self.run_note_text_box = qtw.QTextEdit(self)
        self.run_note.setFixedHeight(50)  # Set the desired height
        run_note_layout.addWidget(self.run_note_text_box) 
        self.submit_run_note_btn = qtw.QPushButton("Submit Note")
        run_note_layout.addWidget(self.submit_run_note_btn)
        self.run_note.setLayout(run_note_layout)

        self.submit_run_note_btn.clicked.connect(self.submit_run_note)

        self.main_layout.addWidget(self.run_note)

        self.BB_monitor = BumpBondMonitor("boop")
        self.main_layout.addWidget(self.BB_monitor)

    @Slot()
    def submit_run_note(self):
        # gaurd conditions
        # if run is not configured dont do anything
        if not hasattr(self, 'run_config'):
            return
        run_note = dm.RunNote(
            run = self.run_config.Run.run,
            note = self.run_note_text_box.toPlainText()
        )
        self.session.add(run_note)
        self.session.commit()
        self.run_note_text_box.clear()

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

    def no_measurement_pending(self):
        for mod_cont in self.module_controllers:
            for sensor in mod_cont.sensors:
                sensor.measurement_pending = False

    @Slot()
    def configure_from_run_config(self):
        """
        This method is the master method for adding all the information form
        the run configuration
        """
        run_config_modal = RunConfigModal(self.session)

        if run_config_modal.exec():
            self.run_config: RunConfig = run_config_modal.run_config
            self.com_port.connect_by_name(self.run_config.Microcontroller.port)
            
            if len(self.run_config.Modules) != 1:
                raise NotImplementedError("multi modules is not implemented yet")
            
            for mod_config in self.run_config.Modules:
                firmware_name = self.run_config.Microcontroller.firmware_version

                module_controller = ModuleController(
                    mod_config.module.name,
                    mod_config.disabled_sensors,
                    fw.firmware_select(firmware_name), 
                    write_interval=MODULE_WRITE_TIMER
                )
                # attach database information to the module controller
                module_controller.config: ModuleConfig = mod_config
                
                self.live_readout_btn.toggled.connect(module_controller.write_timer)
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
            self.run_banner.setText(f"Selected Run: {self.run_config.Run.run}")

        else:
            # remove all data and reset the page if there is any
            # if theres not do nothing!
            print("Cancel!")

    def save_data(self, module_controller:ModuleController, sensor_name:str, raw_adc:str):
        mod_config = module_controller.config
        # print("in save data")
        data = dm.Data(
            run = self.run_config.Run.run,
            control_board = mod_config.control_board,
            control_board_position = mod_config.control_board_position,
            module = mod_config.module,
            module_orientation = mod_config.orientation,
            plate_position = mod_config.cold_plate_position,
            sensor = sensor_name,
            timestamp = datetime.now(),
            raw_adc = raw_adc
        )

        self.session.add(data)
        self.session.commit()

    # NEED THIS TO TRIGGER EVERY 3 or so seconds and read from db
    @Slot(int)
    def update_plot(self) -> None:
        if not hasattr(self, "run_config"):
            return
        for mod_controller in self.module_controllers:
            for sensor in mod_controller.enabled_sensors:
                query = select(dm.Data).where(
                    dm.Data.run==self.run_config.Run.run, 
                    dm.Data.sensor==sensor, 
                    dm.Data.module == mod_controller.config.module
                )

                data = self.session.execute(query).scalars().all()
                if not data:
                    return
                
                t0 = data[0].timestamp
                elapsed_time = lambda t: (t - t0).total_seconds() / 60 
                elapsed_times = [elapsed_time(d.timestamp) for d in data]

                if self.data_select_dropdown.currentData() == "volts":
                    y_data = [d.volts for d in data if d.volts is not None]
                elif self.data_select_dropdown.currentData() == "ohms":
                    y_data = [d.ohms for d in data if d.ohms is not None]
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