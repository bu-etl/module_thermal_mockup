import PySide6.QtWidgets as qtw
from PySide6.QtSerialPort import QSerialPort, QSerialPortInfo
from PySide6.QtCore import Signal, Slot, QIODevice, QTextStream, QTimer
import time

class ComPort(qtw.QComboBox):
    """
    Signals: log_message, data_read_signal \n
    """

    log_message = Signal(str)  # Signal to propagate log messages
    read = Signal(str) # Signal to propogate to Sensors

    def __init__(self, read_rate):
        super(ComPort, self).__init__()
        self.port = None

        self.clear()
        self.addItem('Select Port')
        for port_info in QSerialPortInfo.availablePorts():
            self.addItem(port_info.portName(), port_info)

        #The Signal of a QComboBox - if current index change 
        self.currentIndexChanged.connect(self.select_port) 

        # Set up continuous reading
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._read)
        self.timer.start(read_rate) # ms 

    @Slot() #can be made type safe 
    def select_port(self) -> None:
        ''' Slot for when a port is selected from the dropdown'''
        index = self.currentIndex()
        if index > 0:  # Ignoring the first 'Select Port' line
            port_info = self.itemData(index)
            self.connect_port(port_info)

    def connect_port(self, port: QSerialPortInfo) -> None:
        """Connects and sets port to the corresponding port info"""
        self.disconnect_port() #if already connected to another port, disconnect
        self.log(f"Connecting to port: {port.portName()}")
        self.port = QSerialPort(port)

        self.port.baudRate = QSerialPort.BaudRate.Baud9600
        #self.port.baudRate = QSerialPort.BaudRate.Baud115200
        self.port.breakEnabled = False
        self.port.dataBits = QSerialPort.DataBits.Data8
        self.port.flowControl = QSerialPort.FlowControl.NoFlowControl
        self.port.parity = QSerialPort.Parity.NoParity
        self.port.stopBits = QSerialPort.StopBits.OneStop
        if not self.port.open(QIODevice.ReadWrite):
            self.port = None
            self.log(f"Failed to open port: {port.portName()}")
            return
        self.port.clear()
        self.log(f"Successfully connected to: {port.portName()}")
        # self.port._error_handler = self.port.errorOccurred.connect(self.log_port_error)

    def _read(self) -> str:
        if self.port is None:
            return
        data = self.port.readLine()
        data = QTextStream(data).readAll().strip()
        if data:
            #EMITS DATA READ SIGNAL
            self.read.emit(data)
        return data
    
    def _write(self, message: str) -> None:
        if self.port is not None:
            print(f"COMPORT WRITE MESSAGE: {message}")
            self.port.write(message.encode() + b'\n')
    
    def disconnect_port(self) -> None:
        if self.port is not None:
            # if hasattr(self.port, '_error_handler'):
            #     self.port.errorOccurred.disconnect(self.port._error_handler)
            self.port.close()
            self.log(f"Disconnected from port: {self.port.portName()}")
            self.setCurrentIndex(0)
            self.port = None

    def log(self, message: str) -> None:
        ''' Emit log messages via signal '''
        #when a signal is emitted, any widget (slot) connected to it triggers
        self.log_message.emit(message)