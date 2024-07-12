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

APP = None
ENABLED_CHANNELS = [1, 2, 3, 4, 5, 6, 7, 8]


class MainWindow(qtw.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Howdy Doody")

        self.measurement_data = {i: [] for i in ENABLED_CHANNELS}
        self.measurement_counter = {i: 0 for i in ENABLED_CHANNELS}
        self.measurements_pending = set()
        self.run_start_time = None

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

        self.calibrate_button = qtw.QPushButton('Calibrate')
        self.calibrate_button.clicked.connect(self.start_calibrate)
        self.reset_button = qtw.QPushButton('Reset ADC')
        self.reset_button.clicked.connect(self.reset_adc)

        self.measure_button = qtw.QPushButton('Readout Channels')
        self.measure_button.clicked.connect(self.readout_adc)
        self.measure_checkbox = qtw.QCheckBox('Continuous Readout')

        self.ref_button = qtw.QPushButton('Readout Temp Probes')
        self.ref_button.clicked.connect(self.readout_ref)

        main_layout.addWidget(self.calibrate_button)
        main_layout.addWidget(self.reset_button)
        main_layout.addWidget(self.ref_button)
        main_layout.addWidget(self.measure_button)
        main_layout.addWidget(self.measure_checkbox)

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
        self.readback_timer.interval = 100  # ms
        self.readback_timer.timeout.connect(self.read_port)

        # CSV file setup
        self.csv_filename = f'calibration-data-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.csv'
        with open(self.csv_filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Timestamp', 'Channel', 'ADC Value', 'Volts', 'Ohms'])

    def connect_com_port(self, port_info):
        self.disconnect_com_port()
        self.log(f"Connecting to port: {port_info.portName()}")
        self.port = QSerialPort(port_info)
 #       self.port.baudRate = QSerialPort.BaudRate.Baud9600
        self.port.baudRate = QSerialPort.BaudRate.Baud115200
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
            volts = 1.65 + (int(value, 16) / 2**23 - 1) * (1.024*1.65/1)
            ohms = 1E3 / (3.3 / volts - 1)
            dt_minutes = (datetime.now() - self.run_start_time).seconds / 60
            if ohms > self.history_chart_max:
                self.history_chart_max = ohms
            if ohms < self.history_chart_min:
                self.history_chart_min = ohms
            self.measurement_counter[channel_id] += 1
            idx = self.measurement_counter[channel_id]
            self.measurement_data[channel_id].append((dt_minutes, ohms))
            self.history_chart_series[channel_id].append(dt_minutes, ohms)
            delta = ohms - self.measurement_data[channel_id][0][1]
            self.value_displays[channel_id].text = f"Ch {channel_id}: {ohms:0.6f} {delta:0.6f} ADC READING: {value}"

            # Append data to CSV file
            with open(self.csv_filename, 'a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([datetime.now().isoformat(), channel_id, f"0x{value}", volts, ohms])

            n_points = 300
            if idx > n_points:
                self.history_chart_series[channel_id].remove(0)
                self.measurement_data[channel_id].pop(0)
            self.history_chart.axes(Qt.Orientation.Horizontal)[0].setRange(self.measurement_data[channel_id][0][0],
                                                                           self.measurement_data[channel_id][-1][0])
            y_range = self.history_chart_max - self.history_chart_min
            # self.history_chart.axes(Qt.Orientation.Vertical)[0].setRange(self.history_chart_min - y_range*0.1,
            #                                                              self.history_chart_max + y_range*0.1)
            self.history_chart.axes(Qt.Orientation.Vertical)[0].setRange(700,
                                                                         900)

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


def main():
    global PORT, APP
    APP = qtw.QApplication()
    window = MainWindow()
    window.resize(800, 600)
    window.show()
    # port_selection = SerialPopup.get_port_selection()
    # if port_selection is None:
    # print(port_selection)
    sys.exit(APP.exec())


if __name__ == "__main__":
    main()