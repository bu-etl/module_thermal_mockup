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
from module import ModuleTemperatureMonitor
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
        self.module_temperature_monitors: list[ModuleTemperatureMonitor] = []
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

        #---------------------------End of Tool Bar-----------------------------#

        central_widget = qtw.QWidget()
        self.main_layout = qtw.QVBoxLayout(central_widget)

        self.run_banner = qtw.QLabel("No run selected")
        self.run_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.run_banner.setStyleSheet("color: blue; font-size: 16px; font-weight: bold;")
        self.main_layout.addWidget(self.run_banner)


        readout_btns = qtw.QWidget()
        readout_btn_layout = qtw.QHBoxLayout(readout_btns)

        self.update_timer = QTimer()
        self.live_readout_btn = qtw.QPushButton('Start', self)
        self.live_readout_btn.setCheckable(True)
        self.live_readout_btn.toggled.connect(
            lambda checked: self.live_readout_btn.setText('Start' if not checked else 'Stop')
        )
        self.live_readout_btn.toggled.connect(
            lambda checked: self.update_timer.start(1500) if checked else self.update_timer.stop()
        )

        readout_btn_layout.addWidget(self.live_readout_btn, stretch=1)  

        self.main_layout.addWidget(readout_btns)

        self.serial_display = qtw.QPlainTextEdit()
        self.serial_display.setReadOnly(True)
        self.main_layout.addWidget(self.serial_display, stretch=0)

        self.setCentralWidget(central_widget)

        self.com_port.log_message[str].connect(self.log) 
        self.com_port.read[str].connect(self.log)

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

        self.configure_from_run_config()

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
        run_config_modal = RunConfigModal(self.session)

        if run_config_modal.exec():
            
            self.run_config: RunConfig = run_config_modal.run_config
            self.com_port.connect_by_name(self.run_config.Microcontroller.port)
            
            if len(self.run_config.Modules) != 1:
                raise NotImplementedError("multi modules is not implemented yet")
            
            for mod_config in self.run_config.Modules:
                firmware_name = self.run_config.Microcontroller.firmware_version

                firmware = fw.firmware_select(firmware_name)

                module = ModuleTemperatureMonitor(
                    self.run_config.Run.run,
                    mod_config,
                    firmware,
                    self.com_port,
                    self.update_timer,
                    self.session
                )
                self.module_temperature_monitors.append(module)
                self.main_layout.addWidget(module)

                self.BB_monitor = BumpBondMonitor(
                    mod_config.module.name, 
                    [1,2,3,4], 
                    firmware, 
                    self.com_port,
                    self.update_timer)
                
                self.main_layout.addWidget(self.BB_monitor)

            self.session.commit() # this is for any new runs that have been added to the session
            self.run_banner.setText(f"Selected Run: {self.run_config.Run.run}")

        else:
            # remove all data and reset the page if there is any
            # if theres not do nothing!
            print("Cancel!")
    
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