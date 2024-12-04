import PySide6.QtWidgets as qtw
from PySide6.QtCore import Slot
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from database.env import DATABASE_URI
import database.models as dm
import pyqtgraph as pg
import sys
from widgets.run_config import RunConfigDropdown

class MainWindow(qtw.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Howdy Doody")

        #------------------CREATE DB SESSION---------------------#
        engine = create_engine(DATABASE_URI)
        Session = scoped_session(sessionmaker(bind=engine))
        self.session = Session()
        #--------------------------------------------------------#

        central_widget = qtw.QWidget()
        main_layout = qtw.QVBoxLayout(central_widget)

        main_layout.addWidget(RunConfigDropdown(self.session))

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


if __name__ == "__main__":
    app = qtw.QApplication()

    window = MainWindow()
    window.resize(800, 800)
    window.show()

    # window.session.close()
    sys.exit(app.exec())