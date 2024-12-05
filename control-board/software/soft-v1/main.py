import PySide6.QtWidgets as qtw
from PySide6.QtCore import Slot
from PySide6.QtGui import QAction
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from database.env import DATABASE_URI
import database.models as dm
import pyqtgraph as pg
import sys
from widgets.run_config import RunConfigModal
from widgets.com_port import ComPort

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
    
        central_widget = qtw.QWidget()
        main_layout = qtw.QVBoxLayout(central_widget)

        #main_layout.addWidget(RunConfigDropdown(self.session))

        readout_info = qtw.QWidget()
        readout_info_layout = qtw.QHBoxLayout(readout_info)

        self.CelciusTimePlot = pg.PlotWidget(title="Temperature Over Time", background="#f5f5f5")
        self.CelciusTimePlot.addLegend()
        self.CelciusTimePlot.showGrid(x=True, y=True)
        self.CelciusTimePlot.setLabel('left', 'Celcius')  # Y-axis label
        self.CelciusTimePlot.setLabel('bottom', 'Minutes')  # X-axis label
        self.celcius_time_plots = {}
        # for channel, sensor in self.module.sensors.items():
        #     # Initialize plotItem for each sensor name
        #     self.ohm_time_plots[channel] = self.CelciusTimePlot.plot(
        #         [], [], #x, y
        #         pen=self.module.color_map[channel], 
        #         name=sensor.name
        #     )
        readout_info_layout.addWidget(self.CelciusTimePlot, stretch=1)

        main_layout.addWidget(readout_info)

        self.setCentralWidget(central_widget)

    @Slot()
    def run_config_modal(self):
        dlg = RunConfigModal(self.session)
        if dlg.exec():
            print("Success!")
        else:
            print("Cancel!")

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