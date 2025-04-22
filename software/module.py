from PySide6.QtWidgets import QWidget
import PySide6.QtWidgets as qtw
import pyqtgraph as pg
from PySide6.QtCore import Signal, Slot, QTimer
#from run_config import ModuleConfig
from firmware_interface import ModuleFirmwareInterface
from com_port import ComPort
from sqlalchemy.orm import scoped_session
from database import models as dm
from datetime import datetime
from run_config import ModuleConfig
from sqlalchemy import select
from functools import partial

SENSOR_NAMES = ["E1", "E2", "E3", "E4", "L1", "L2", "L3", "L4", "P1", "P2", "P3"]

class ModuleTemperatureMonitor(QWidget):
    """
    Used for reading out the temperatures on the thermal mockup module
    """

    def __init__(self, run:dm.Run, config: ModuleConfig, firmware: ModuleFirmwareInterface, com_port: ComPort, timer: QTimer, db_session: scoped_session):
        super(ModuleTemperatureMonitor, self).__init__()

        self.run = run
        self.config = config
        self.name = self.config.module.name
        self.disabled_sensors = self.config.disabled_sensors

        self.enabled_sensors = list(set(SENSOR_NAMES) - set(self.disabled_sensors))
        self.firmware = firmware
        self.com_port = com_port
        self.timer = timer
        self.session = db_session

        self.measurement_pendings = {s: False for s in self.enabled_sensors}

        self.color_map = {
            "E3": "#9e0202", #dark red
            "L1": "#00ff00", #lime green
            "E1": "#006400", #dark green
            "L2": "#1e90ff", #dodger blue
            "E2": "#191970", #midnightblue
            "L3": "#ff385d", #salmon red pink
            "L4": "#ffd700", #gold
            "E4": "#a39b00",  #mustard yellow
            "P1": "black",
            "P2": "black",
            "P3": "black"
        }

        self.main_layout = qtw.QVBoxLayout(self)
        self.setLayout(self.main_layout)

        self.select_sensor_dropdown = qtw.QComboBox()
        self.select_sensor_dropdown.addItem('Select Sensor')
        self.main_layout.addWidget(self.select_sensor_dropdown, stretch=0)

        self.data_select_dropdown = qtw.QComboBox()
        self.data_select_dropdown.addItem('Data Type')
        self.main_layout.addWidget(self.data_select_dropdown, stretch=0)
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

        self.button = qtw.QPushButton(self.name, self)
        self.button.setCheckable(True)
        self.main_layout.addWidget(self.button)

        self.temperature_plot = pg.plot(title="Temperature Monitor", background="#f5f5f5")
        self.temperature_plot.showGrid(x=True, y=True)
        self.temperature_plot.setLabel('left', 'Data')
        self.temperature_plot.setLabel('bottom', 'Minutes')

        self.button.clicked.connect(self.toggle_show)
        self.main_layout.addWidget(self.temperature_plot, stretch=1)

        self.temp_save = {s: [] for s in self.enabled_sensors}

        self.com_port.read[str].connect(self.save)
        self.timer.timeout.connect(self.write_sensors)
        self.timer.timeout.connect(self.update_plot)

    def toggle_show(self):
        self.temperature_plot.setVisible(not self.temperature_plot.isVisible())

    def save(self, raw_output:str):
        # i love python
        data = self.firmware.read_sensor(raw_output) or self.firmware.read_probe(raw_output)
        if not data:
            return

        sensor, raw_value = data
        if sensor not in self.enabled_sensors:
            return
        
        self.measurement_pendings[sensor] = False

        # print("in save data")
        data = dm.Data(
            run = self.run,
            control_board = self.config.control_board,
            control_board_position = self.config.control_board_position,
            module = self.config.module,
            module_orientation = self.config.orientation,
            plate_position = self.config.cold_plate_position,
            sensor = sensor,
            timestamp = datetime.now(),
            raw_adc = raw_value
        )

        self.session.add(data)
        self.session.commit()

    def write_sensors(self) -> str:
        if all(self.measurement_pendings.values()):
            # Make sure you have read all values before trying to read bumps again
            return
        
        # have to do it like this because I was dumb before and combined probes and silicon sensors...
        sensor_names = [s for s in self.enabled_sensors if 'p' not in s.lower()]
        probe_names = [p for p in self.enabled_sensors if 'p' in p.lower()]
        command = self.firmware.write_sensors(sensor_names) + "\n"  + self.firmware.write_probes(probe_names)
        self.com_port._write(command)

        # measurements are now pending!
        for s in self.enabled_sensors:
            self.measurement_pendings[s] = True

        return command
    
    def update_plot(self):
        for i, sensor in enumerate(self.enabled_sensors):
            query = select(dm.Data).where(
                dm.Data.run==self.run, 
                dm.Data.sensor==sensor, 
                dm.Data.module == self.config.module
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

            self.temperature_plot.plot(
                elapsed_times, y_data,
                pen=(i, len(self.sensors))
            )