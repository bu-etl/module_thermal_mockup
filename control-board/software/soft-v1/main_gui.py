import PySide6.QtWidgets as qtw
from PySide6.QtCore import Slot
from PySide6.QtGui import QAction
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from database.env import DATABASE_URI
import database.models as dm
import pyqtgraph as pg
import sys
from run_config import RunConfigModal
from com_port import ComPort
from module import Module
import firmware_interface as fw
from functools import partial

ENABLED_CHANNELS = ['E1', 'E2', 'E3', 'E4', 'L1', 'L2', 'L3', 'L4']

class MainWindow(qtw.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Howdy Doody")

        #------------------CREATE DB SESSION---------------------#
        engine = create_engine(DATABASE_URI)
        Session = scoped_session(sessionmaker(bind=engine))
        self.session = Session()
        #--------------------------------------------------------#

        #--------------------------------MENU BAR-------------------------------#
        self.menu = self.menuBar()

        #Run Menu
        self.run_menu = self.menu.addMenu('Run')
        
        # What an action is -> https://www.pythonguis.com/tutorials/pyside6-actions-toolbars-menus/
        run_config_action = QAction('Choose Run Config', self)
        run_config_action.triggered.connect(self.run_config_modal)
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

        self.modules = []

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
        main_layout.addWidget(readout_btns)


        readout_info = qtw.QWidget()
        readout_info_layout = qtw.QHBoxLayout(readout_info)

        self.CelciusTimePlot = pg.PlotWidget(title="Temperature Over Time", background="#f5f5f5")
        self.CelciusTimePlot.addLegend()
        self.CelciusTimePlot.showGrid(x=True, y=True)
        self.CelciusTimePlot.setLabel('left', 'Celcius')  # Y-axis label
        self.CelciusTimePlot.setLabel('bottom', 'Minutes')  # X-axis label
        self.celcius_time_plots = {}

        readout_info_layout.addWidget(self.CelciusTimePlot, stretch=1)

        self.serial_display = qtw.QPlainTextEdit()
        self.serial_display.setReadOnly(True)
        readout_info_layout.addWidget(self.serial_display, stretch=0)


        main_layout.addWidget(readout_info)

        self.setCentralWidget(central_widget)

        self.com_port.log_message[str].connect(self.log) 
        self.com_port.read[str].connect(self.log)

    def write_adc_action(self, name: str, adc_command: str) -> QAction:
        """
        Used for generalizing the adding of toolbar buttons
        """
        write_action = QAction(name, self)
        write_action.triggered.connect(partial(self.com_port._write, adc_command))
        return write_action

    @Slot()
    def run_config_modal(self):
        run_config_modal = RunConfigModal(self.session)
        if run_config_modal.exec():
            # load all the config data! This even means previous data
            
            # commit new run if new run
            run_config = run_config_modal.run_config
            if len(run_config.modules) != 1:
                raise NotImplementedError("multi modules is not implemented yet")
            
            for mod_config in run_config.modules:
                self.modules.append(
                    Module(mod_config, ENABLED_CHANNELS, fw.ThermalMockupV2(), readout_interval=1)
                )
            self.temporary_method_init_module_for_non_control_board_fw()

        else:
            # remove all data and reset the page if there is any
            # if theres not do nothing!
            print("Cancel!")

    def temporary_method_init_module_for_non_control_board_fw(self):

        for module in self.modules:
            self.live_readout_btn.toggled.connect(module.live_readout)
            for sensor in module.sensors:
                self.select_sensor_dropdown.addItem(
                    f"{module.name}_{sensor.name}", sensor
                )

            for sensor in module.sensors:
                # Initialize plotItem for each sensor name
                self.celcius_time_plots[f"{module.name}_{sensor.name}"] = self.CelciusTimePlot.plot(
                    [], [], #x, y
                    pen=module.color_map[sensor.name], 
                    name=sensor.name
                )
        
            module.write[str].connect(self.com_port._write)
            self.com_port.read[str].connect(module._read)
            module.read[str].connect(self.update_plot)

    @Slot(int)
    def update_plot(self, sensor_name: str) -> None:
        for module in self.modules:
            sensor = module.sensor(sensor_name)
            if sensor is not None and sensor.raw_adcs:
                t0 = sensor.times[0]
                elapsed_time = lambda t: (t - t0).total_seconds() / 60 
                elapsed_times = [elapsed_time(t) for t in sensor.times]

                self.celcius_time_plots[f"{module.name}_{sensor.name}"].setData(
                    elapsed_times, sensor.ohms
                )

    @Slot(str)
    def log(self, text: str) -> None:
        self.serial_display.appendPlainText(text)

    @Slot()
    def _close(self) -> None:
        self.com_port.disconnect_port()
        self.close()


if __name__ == "__main__":
    app = qtw.QApplication()

    window = MainWindow()
    window.resize(800, 800)
    window.show()

    # window.session.close()
    sys.exit(app.exec())