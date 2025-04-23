"""
This widget is used to readout the bump bonds and plot
"""
import PySide6.QtWidgets as qtw
import pyqtgraph as pg
from PySide6.QtCore import Slot, QTimer, Qt, Signal
from firmware_interface import ModuleFirmwareInterface
from com_port import ComPort
from datetime import datetime
import time
from database import models as dm
from sqlalchemy.orm import scoped_session
from run_config import ModuleConfig

class BumpBondMonitor(qtw.QFrame):
    # write = Signal(str)

    def __init__(self, name: str, run: dm.Run, module_config: ModuleConfig, bb_path_ids: list[str], firmware: ModuleFirmwareInterface, com_port: ComPort, timer: QTimer, db_session: scoped_session):
        """
        bb_path_ids: are the ids that is used to input into the firmware. EX: TP 1, 1 is the bb_path_id
        """
        
        super(BumpBondMonitor, self).__init__()

        self.setFrameShape(qtw.QFrame.Shape.Box)
        self.setFrameShadow(qtw.QFrame.Shadow.Raised)
        self.setLineWidth(2)
        self.setContentsMargins(6, 6, 6, 6)

        self.setStyleSheet("""
            QFrame {
                border: 2px solid green;        /* width, style, color */
                background-color: white;        /* optional fill */
            }
        """)

        self.name = name
        self.run = run
        self.module_config = module_config
        self.bb_path_ids = bb_path_ids
        self.firmware = firmware
        self.com_port = com_port
        self.timer = timer

        self.measurement_pendings = {bb_id: False for bb_id in bb_path_ids}

        # layout with a button and empty plot that can hide/show
        self.main_layout = qtw.QVBoxLayout(self)
        self.setLayout(self.main_layout)

        self.button = qtw.QPushButton(name, self)
        self.button.setCheckable(True)
        self.main_layout.addWidget(self.button)

        self.bb_plot = pg.plot(title="Three plot curves")
        self.bb_plot.showGrid(x=True, y=True)
        self.bb_plot.setLabel('left', 'Resistance')
        self.bb_plot.setLabel('bottom', 'Minutes')

        self.button.clicked.connect(self.toggle_show)
        self.main_layout.addWidget(self.bb_plot)

        self.temp_save = {bb_id: [] for bb_id in bb_path_ids}

        # READ AND SAVE SIGNAL/SLOTS
        #self.write[str].connect(self.com_port._write)
        self.com_port.read[str].connect(self.save)

        self.timer.timeout.connect(self.write_bb)
        self.timer.timeout.connect(self.update_plot)

    def toggle_show(self):
        self.bb_plot.setVisible(not self.bb_plot.isVisible())

    def save(self, raw_output: str):
        # will need to extract bb id
        # will need to extract raw_adc from it
        data = self.firmware.read_bb(raw_output)
        if not data:
            return
    
        bb_path_id, value = data
        if bb_path_id not in self.bb_path_ids:
            return

        # convert to resistance?  yea but for now just do voltage
        self.measurement_pendings[bb_path_id] = False

        # do the saving for now just append to list will go to db later
        # will need to pass in the db session but its fine
        self.temp_save[bb_path_id].append((time.perf_counter(), value))

        #data = dm.BbResistancePathData()
    
    def write_bb(self):
        if all(self.measurement_pendings.values()):
            # Make sure you have read all values before trying to read bumps again
            return
        command = self.firmware.write_bbs(self.bb_path_ids)
        for bb_id in self.bb_path_ids:
            self.measurement_pendings[bb_id] = True

        self.com_port._write(command)
        return command
    
    def update_plot(self):
        # this should fetch whatever is in the db and plot it periodically
        for bb_id, data in self.temp_save.items():
            if not data:
                continue
            y_data = [d[1] for d in data]
            x_data = [d[0] for d in data]

            self.bb_plot.plot(x_data, y_data, 
                              pen=(bb_id,len(self.bb_path_ids)))

