import PySide6
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
from sqlalchemy.orm import Session, scoped_session, sessionmaker
from database.env import DATABASE_URI
import argparse
import database.models as dm
from typing import Literal
from functools import partial

class RunConfigModal(qtw.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("HELLO!")

        QBtn = (
            qtw.QDialogButtonBox.Ok | qtw.QDialogButtonBox.Cancel
        )

        self.buttonBox = qtw.QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = qtw.QVBoxLayout()
        message = qtw.QLabel("Something happened, is that OK?")
        layout.addWidget(message)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)

class MainWindow(qtw.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Howdy Doody")

        button = qtw.QPushButton("Choose Run Config")
        button.clicked.connect(self.open_run_config_modal)
        self.setCentralWidget(button)  

    def open_run_config_modal(self, s):
        print("click", s)

        dlg = RunConfigModal()
        if dlg.exec():
            print("Success!")
        else:
            print("Cancel!")
     

if __name__ == "__main__":
    app = qtw.QApplication()

    window = MainWindow()
    window.resize(800, 800)
    window.show()

    # window.session.close()
    sys.exit(app.exec())