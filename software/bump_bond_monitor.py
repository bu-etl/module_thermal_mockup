"""
This widget is used to readout the bump bonds and plot
"""
import PySide6.QtWidgets as qtw
import pyqtgraph as pg
from PySide6.QtCore import Slot, QTimer, Qt
from firmware_interface import ModuleFirmwareInterface
from com_port import ComPort
class BumpBondMonitor(qtw.QWidget):
    
    def __init__(self, name: str, bb_path_ids: list, firmware: ModuleFirmwareInterface, com_port: ComPort):
        super(BumpBondMonitor, self).__init__()

        self.name = name
        self.firmware = firmware
        self.com_port = com_port
        self.bb_path_ids = bb_path_ids
        self.measurement_pendings = {bb_id: False for bb_id in bb_path_ids}

        # layout with a button and empty plot that can hide/show
        self.main_layout = qtw.QVBoxLayout(self)
        self.setLayout(self.main_layout)

        self.button = qtw.QPushButton(name, self)
        self.button.setCheckable(True)
        self.main_layout.addWidget(self.button)

        self.BB_Plot = pg.PlotWidget(background="#f5f5f5")
        self.BB_Plot.showGrid(x=True, y=True)
        self.BB_Plot.setLabel('left', 'Resistance')
        self.BB_Plot.setLabel('bottom', 'Minutes')

        self.button.clicked.connect(self.toggle_show)
        self.main_layout.addWidget(self.BB_Plot)

        self.reading_timer = QTimer()
        self.reading_timer.timeout.connect(self.read_bb)
        self.reading_timer.start(3000)


        self.temp_save = {bb_id: [] for bb_id in bb_path_ids}

    def toggle_show(self):
        self.BB_Plot.setVisible(not self.BB_Plot.isVisible())

    def save(self, raw_output: str):
        # will need to extract bb id
        # will need to extract raw_adc from it

        data = self.firmware.read_bb(raw_output)
        if not data:
            return
    
        bb_path_id, value = data

        # convert to resistance?  yea but for now just do voltage
        self.measurement_pendings[bb_path_id] = False

        # do the saving for now just append to list will go to db later
        # will need to pass in the db session but its fine
        self.temp_save[bb_path_id].append(value)
        
    def write_bb(self, bb_path_ids: list[int]):
        if not all(self.measurement_pendings.values()):
            """Make sure you have read all values before trying to read bumps again"""
            return
        command = self.firmware.write_bb(bb_path_ids)
        self.com_port._write(command)
        for bb_id in bb_path_ids:
            self.measurement_pendings[bb_id] = True

    def update_plot(self):
        ...
        # this should fetch whatever is in the db and plot it periodically