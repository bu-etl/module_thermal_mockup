import PySide6
from __feature__ import true_property  # noqa
import sys
import csv
from collections import deque
from datetime import datetime
import PySide6.QtWidgets as qtw
import PySide6.QtCharts as qtc
from PySide6.QtSerialPort import QSerialPort, QSerialPortInfo
from PySide6 import QtCore
from PySide6.QtCore import Qt
from sqlalchemy import create_engine, select, Engine
from sqlalchemy.orm import Session
from env import DATABASE_URI
import argparse
import data_models as dm
from typing import Literal

APP = None
ENABLED_CHANNELS = [1, 3, 7, 8]
DB_RUN_MODES = ('TEST', 'DEBUG', 'REAL')
DATA_STORE = ['LOCAL', 'DB']
channel_equations = {
    1: lambda ohms: (ohms - 723.5081039009991) / 3.0341696569667955,
    3: lambda ohms: (ohms - 740.9934812257274) / 3.6682463501270317,
    7: lambda ohms: (ohms - 843.5650697047028) / 3.5332573008093036,
    8: lambda ohms: (ohms - 735.6945560895681) / 3.0846916504139346,
}

channel_sensor_map = {
    1: 'E3',
    2: 'L1',
    3: 'E1',
    4: 'L2',
    5: 'E2',
    6: 'L3',
    7: 'L4',
    8: 'E4'
}

def init_db_run(engine: Engine, run_id: int|None = None, comment: str|None = None, mode: str|None = None):
    """
    Returns the Run row from the database for this selected run (either an old run or creates a new one dependng on the arguments)

    If run_id is specified then it will just fetch that row. If comment AND mode are specifed it makes a new run.
    """
    if run_id is not None and comment is not None and mode is not None:
        raise ValueError("ambiguous input, please only give run_id for having this data be apart of an old run, OR give a mode and comment for a new run.")
    if run_id is not None:
        query = select(dm.Run).where(dm.Run.id == run_id)
        with Session(engine) as session:
            run = session.execute(query).one() #or use first and raise your owne error
            print(f'Using old run {run}')
            return run
    elif comment is not None and mode is not None:
        with Session(engine) as session:
            run = dm.Run(
                comment = comment,
                mode = mode
            )
            session.add(run)
            session.commit()
            print(f'Added new run to db {run}')
            return run
    else:
        raise ValueError("Please give both a comment and mode for a this new run.")


class MainWindow(qtw.QMainWindow):
    def __init__(self, args: argparse.Namespace):
        super().__init__()
        self.setWindowTitle("Howdy Doody")
        
        #get parsed arguments
        self.module_name = args.module
        self.data_store = args.data_store

        banner_text = ''
        if self.data_store == 'DB':
            self.engine = create_engine(DATABASE_URI)
            self.data_run = init_db_run(self.engine, run_id=args.run_id, comment=args.comment, mode=args.mode)
            banner_text = str(self.data_run)
        elif self.data_store == 'LOCAL':
            #if csv file has not been made, create it
            self.csv_filename = f'{self.module_name}-calibration-data-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.csv'
            with open(self.csv_filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Timestamp', 'Channel', 'ADC Value', 'Volts', 'Ohms', 'Temp'])
            banner_text = f'STORING DATA LOCALLY IN CSV NAMED: {self.csv_filename}'
        else:
            raise NotImplementedError(f"Sorry this form of data storing is not supported: {self.data_store}")
        
        self.measurement_data = {i: [] for i in ENABLED_CHANNELS}
        self.measurement_counter = {i: 0 for i in ENABLED_CHANNELS}
        self.measurements_pending = set()
        self.run_start_time = None

        #--------GUI LAYOUT-------------#
        self.menu = self.menuBar()
        self.file_menu = self.menu.addMenu('File')
        self.connect_menu = self.menu.addMenu('Connect')

        exit_action = self.file_menu.addAction('Exit', self._close)
        exit_action.shortcut = 'Ctrl+Q'

        self.port = None
        self.port_infos = QSerialPortInfo.availablePorts()
        for port_info in self.port_infos:
            self.connect_menu.addAction(port_info.portName(), lambda: self.connect_com_port(port_info))

        central_widget = qtw.QWidget()
        main_layout = qtw.QVBoxLayout(central_widget)

        self.banner_label = qtw.QLabel(banner_text)
        self.banner_label.setStyleSheet("background-color: #FFD700; color: #000000; padding: 10px; font-size: 16px;")

        self.calibrate_button = qtw.QPushButton('Calibrate')
        self.calibrate_button.clicked.connect(self.start_calibrate)
        self.reset_button = qtw.QPushButton('Reset ADC')
        self.reset_button.clicked.connect(self.reset_adc)

        self.measure_button = qtw.QPushButton('Readout Channels')
        self.measure_button.clicked.connect(self.readout_adc)
        self.measure_checkbox = qtw.QCheckBox('Continuous Readout')

        self.ref_button = qtw.QPushButton('Readout Temp Probes')
        self.ref_button.clicked.connect(self.readout_ref)

        main_layout.addWidget(self.banner_label)
        main_layout.addWidget(self.calibrate_button)
        main_layout.addWidget(self.reset_button)
        main_layout.addWidget(self.ref_button)
        main_layout.addWidget(self.measure_button)
        main_layout.addWidget(self.measure_checkbox)

        #------PLOT------#
        self.history_chart_view = qtc.QChartView()
        self.history_chart = qtc.QChart()
        self.history_chart_min = 10
        self.history_chart_max = -1

        self.history_chart_view.setChart(self.history_chart)
        self.history_chart_series = {}
        for i in ENABLED_CHANNELS:
            series = qtc.QLineSeries()
            series.name = f'Channel {i}'
            self.history_chart_series[i] = series
            self.history_chart.addSeries(series)

        self.history_chart.createDefaultAxes()

        main_layout.addWidget(self.history_chart_view)

        self.value_displays = {}
        for i in ENABLED_CHANNELS:
            self.value_displays[i] = qtw.QLabel()
            main_layout.addWidget(self.value_displays[i])

        self.serial_display = qtw.QPlainTextEdit()
        self.serial_display.readOnly = True

        main_layout.addWidget(self.serial_display)

        self.setCentralWidget(central_widget)

        self.readback_timer = QtCore.QTimer(self)
        self.readback_timer.interval = 1000  # ms
        self.readback_timer.timeout.connect(self.read_port)

    def connect_com_port(self, port_info):
        self.disconnect_com_port()
        self.log(f"Connecting to port: {port_info.portName()}")
        self.port = QSerialPort(port_info)
        self.port.baudRate = QSerialPort.BaudRate.Baud9600
        #self.port.baudRate = QSerialPort.BaudRate.Baud115200
        self.port.breakEnabled = False
        self.port.dataBits = QSerialPort.DataBits.Data8
        self.port.flowControl = QSerialPort.FlowControl.NoFlowControl
        self.port.parity = QSerialPort.Parity.NoParity
        self.port.stopBits = QSerialPort.StopBits.OneStop
        if not self.port.open(QtCore.QIODevice.ReadWrite):
            print("Failed to open port!")
            self.port = None
            return
        self.log("Port Opened")
        self.log(f"\t{port_info.description()}")
        self.log(f"\tManufacturer: {port_info.manufacturer()}")
        self.log(f"\tVendor ID: {port_info.vendorIdentifier()}")
        self.log(f"\tProduct ID: {port_info.productIdentifier()}")
        self.log(f"\tSerial Number: {port_info.serialNumber()}")
        self.log(f"\tbaudRate: {self.port.baudRate}")
        self.log(f"\tbreakEnabled: {self.port.breakEnabled}")
        self.log(f"\tdataBits: {self.port.dataBits}")
        self.log(f"\tflowControl: {self.port.flowControl}")
        self.log(f"\tparity: {self.port.parity}")
        self.log(f"\tstopBits: {self.port.stopBits}")
        self.port.clear()
        self.port._error_handler = self.port.errorOccurred.connect(self.log_port_error)
        self.write_port('reset')
        self.readback_timer.start()

    def log_port_error(self, error):
        self.log(error)

    def disconnect_com_port(self):
        if self.port is not None:
            self.log(f"Disconnecting from port: {self.port.portName()}")
            self.readback_timer.stop()
            if hasattr(self.port, '_error_handler'):
                self.port.errorOccurred.disconnect(self.port._error_handler)
            self.port.close()
            self.port = None

    def _close(self):
        self.disconnect_com_port()
        self.close()

    def log(self, text: str):
        self.serial_display.appendPlainText(text)

    def write_port(self, message: str):
        if self.port is None:
            return
        # print(">>> " + message)
        self.log(">>> " + message)
        self.port.write(message.encode() + b'\n')

    def read_port(self) -> None:
        if self.port is None:
            return
        data = self.port.readLine()
        data = QtCore.QTextStream(data).readAll().strip()
        if data:
            self.log("<<< " + data)
        if data.startswith('measure'):
            _, channel_id, value = data.split()
            channel_id = int(channel_id)
            try:
                self.measurements_pending.remove(channel_id)
            except KeyError:
                self.log(f"WARNING: Received unexpected measurement from device, {data}")
            if self.measure_checkbox.checked:
                self.readout_adc()
            num = int(str(value)[:-2],16)
            print(f"Channel {channel_id}: {hex(num)}")
            volts = 2.5 + (num / 2**15 - 1) * 1.024 * 2.5 / 1
            print(f"Channel {channel_id}: {volts:0.6f} V")
            ohms = 1E3 / (5 / volts - 1)
            print(f"Channel {channel_id}: {ohms:0.6f} Ohms")
            
            # Calculate temperature using the channel_equations
            if channel_id in channel_equations:
                temp = channel_equations[channel_id](ohms)
                print(f"Channel {channel_id}: {temp:0.6f} °C")
            else:
                temp = None

            dt_minutes = (datetime.now() - self.run_start_time).seconds / 60
            dt_minutes = (datetime.now() - self.run_start_time).seconds / 60

            if temp > self.history_chart_max:
                self.history_chart_max = temp
            if temp < self.history_chart_min:
                self.history_chart_min = temp
            self.measurement_counter[channel_id] += 1
            idx = self.measurement_counter[channel_id]
            self.measurement_data[channel_id].append((dt_minutes, temp))
            self.history_chart_series[channel_id].append(dt_minutes, temp)
            delta = temp - self.measurement_data[channel_id][0][1]
            self.value_displays[channel_id].text = f"Ch {channel_id}: {temp:0.6f} {delta:0.6f} ADC READING: {value}"

            self.save_data({
                'module': self.module_name,
                'channel_id': channel_id,
                'raw_adc': f"0x{value}",
                'voltage': volts,
                'resistance': ohms,
                'temperature': temp
            })

            n_points = 300
            if idx > n_points:
                self.history_chart_series[channel_id].remove(0)
                self.measurement_data[channel_id].pop(0)
            self.history_chart.axes(Qt.Orientation.Horizontal)[0].setRange(self.measurement_data[channel_id][0][0],
                                                                           self.measurement_data[channel_id][-1][0])
            y_range = self.history_chart_max - self.history_chart_min
            # self.history_chart.axes(Qt.Orientation.Vertical)[0].setRange(self.history_chart_min - y_range*0.1,
            #                                                              self.history_chart_max + y_range*0.1)
            self.history_chart.axes(Qt.Orientation.Vertical)[0].setRange(20,
                                                                         80)
    def start_calibrate(self):
        self.write_port('calibrate')

    def reset_adc(self):
        self.write_port('reset')

    def readout_adc(self):
        if self.run_start_time is None:
            self.run_start_time = datetime.now()
        for channel_id in ENABLED_CHANNELS:
            if channel_id not in self.measurements_pending:
                self.measurements_pending.add(channel_id)
                self.write_port(f'measure {channel_id}')

    def readout_ref(self):
        self.write_port('probe 1 2 3')

    def save_data(self, data: dict):
        if self.data_store == 'LOCAL':
            #insert data
            with open(self.csv_filename, 'a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow( [datetime.now().isoformat(), data["channel_id"], data["raw_adc"], data["voltage"], data["resistance"], data["temperature"]] )
        elif self.data_store == 'DB':
            #insert data
            with Session(self.engine) as session:
                query = select(dm.Module).where(dm.Module.name == self.module_name)
                module = session.scalars(query).one()

                db_data = dm.Data(
                    module = module,
                    sensor = channel_sensor_map[data["channel_id"]],
                    timestamp = datetime.now(),
                    raw_adc = data["raw_adc"],
                    volts = data["voltage"],
                    ohms = data["resistance"],
                    celcius = data["temperature"],
                    run = self.data_run
                )
                session.add(db_data)
                session.commit()
        else:
            raise NotImplementedError(f"Sorry this form of data storing is not supported: {self.data_store}")

def main():
    global PORT, APP

    argParser = argparse.ArgumentParser(description = "Argument parser")
    argParser.add_argument('-m','--module', action='store', required=True, help='Module that is being calibrated')
    argParser.add_argument('-ds','--data_store', action='store', choices=DATA_STORE, required=True, help=f'Select where to store data')
    argParser.add_argument('-r','--run_id', action='store', help=f'Database ID of a previous run that you would like this run to be apart of')
    argParser.add_argument('-c', '--comment', action='store', help=f'A comment or description of the new run, only used for new runs')
    argParser.add_argument('-mode', action='store', choices=DB_RUN_MODES)
    args = argParser.parse_args()

    APP = qtw.QApplication()
    #arg_parser = parse(APP)

    # port_selection = SerialPopup.get_port_selection()
    # if port_selection is None:
    # print(port_selection)
    # if arg_parser is not None:
    #     print(arg_parser.value('module'))
    #     print(arg_parser.value('send'))
    window = MainWindow(args)
    window.resize(800, 600)
    window.show()
    sys.exit(APP.exec())

if __name__ == "__main__":
    main()