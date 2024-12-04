import PySide6.QtWidgets as qtw
from PySide6.QtCore import Slot
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from database.env import DATABASE_URI
import database.models as dm
import pyqtgraph as pg
import sys
from run_config import RunConfig
import tomllib
from pydantic import ValidationError
from widgets.collapsable_button import Container



def run_config_preview(db_session, run_config: RunConfig) -> qtw.QWidget:
    # run info preview

    # picture preview

    # module preview

    #----> lets just start by dumping to a text box

    display = qtw.QPlainTextEdit()
    display.setReadOnly(True)

    display.appendPlainText(str(run_config))
    return display

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
        # ------------------ Run Configuration Widget -----------------------#
        container = Container("Run Configuration", color_background=True)
        self.run_configuration_layout = qtw.QGridLayout(container.contentWidget)

        self.config_file_btn = qtw.QPushButton("Select Config File")
        self.config_file_btn.clicked.connect(self.load_run_config)
        self.run_configuration_layout.addWidget(self.config_file_btn)

        main_layout.addWidget(container)
        # -------------------------------------------------------------------#

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
    def load_run_config(self):
        file_path, _ = qtw.QFileDialog.getOpenFileName(
            self, 
            "Select Config File", 
            None,
            "TOML (*.toml)"
        )
        if not file_path:
            # then they exited without selecing file
            return None
        
        with open(file_path, 'rb') as f:
            try:
                self.run_config = RunConfig.model_validate(tomllib.load(f))
                self.run_configuration_layout.addWidget(
                    run_config_preview(self.run_config)
                )
            except ValidationError as e:
                qtw.QMessageBox.critical(
                    self,
                    "Configuration File Format Error",
                    str(e),
                    buttons=qtw.QMessageBox.Retry,
                    defaultButton=qtw.QMessageBox.Retry,
                )

if __name__ == "__main__":
    app = qtw.QApplication()

    window = MainWindow()
    window.resize(800, 800)
    window.show()

    # window.session.close()
    sys.exit(app.exec())