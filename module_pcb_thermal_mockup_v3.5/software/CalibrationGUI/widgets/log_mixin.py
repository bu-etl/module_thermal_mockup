import PySide6.QtWidgets as qtw
from PySide6.QtSerialPort import QSerialPort, QSerialPortInfo
from PySide6.QtCore import Signal, Slot, QIODevice, QTextStream, QTimer

class LogMixin():
    log_message = Signal(str)  # Signal to propagate log messages
    def __init__(self):
        super(LogMixin, self).__init__()
    def log(self, message: str) -> None:
        ''' Emit log messages via signal '''
        #when a signal is emitted, any widget (slot) connected to it triggers
        self.log_message.emit(message)
