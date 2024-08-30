import PySide6.QtWidgets as qtw
from PySide6.QtSerialPort import QSerialPort, QSerialPortInfo
from PySide6.QtCore import Signal, Slot, QIODevice, QTextStream, QTimer

class ComPort(qtw.QComboBox):
    """
    Signals: log_message, data_read_signal \n
    """

    log_message = Signal(str)  # Signal to propagate log messages
    data_read_signal = Signal(str) # Signal to propogate to Sensors

    def __init__(self):
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
        self.timer.timeout.connect(self.read)
        self.timer.start(1000)  # Read data every 1000 ms (1 second)

    @Slot() #can be made type safe 
    def select_port(self):
        ''' Slot for when a port is selected from the dropdown'''
        index = self.currentIndex()
        if index > 0:  # Ignoring the first 'Select Port' line
            port_info = self.itemData(index)
            self.connect_port(port_info)

    def connect_port(self, port):
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

    # GOAL: Emit a signal when data is ready
    #make this a signal of ComPort, reading when read it triggers data to be sent to sensors 
    # -> in mainwindow self.ComPort.read.connect(self.ETROC1.whatever) In there you gotta decide if that is data you want
    def read(self) -> None:
        if self.port is None:
            return
        data = self.port.readLine()
        data = QTextStream(data).readAll().strip()

        self.data_read_signal.emit(data) # need to add slot in sensors to read this data, there they deterine if the data is for them
        return data
    
    def write(self, message: str):
        if self.port is None:
            return
        self.com_port.write(message.encode() + b'\n')
    
    def disconnect_port(self):
        if self.port is not None:
            # if hasattr(self.port, '_error_handler'):
            #     self.port.errorOccurred.disconnect(self.port._error_handler)
            self.port.close()
            self.port = None

    def log(self, message):
        ''' Emit log messages via signal '''
        #when a signal is emitted, any widget (slot) connected to it triggers
        self.log_message.emit(message)