import PySide6.QtWidgets as qtw
from PySide6.QtCore import Slot, Qt, Signal
import pyqtgraph as pg

def is_float(string):
    try:
        float(string)
        return True
    except ValueError:
        return False

class CalibWidget(qtw.QWidget):
    def __init__(self):
        super(CalibWidget, self).__init__()
        main_layout = qtw.QVBoxLayout(self)

        # >>  DELETE CALIBRATION ROW BUTTON
        self.delete_temp_btn = qtw.QPushButton('Delete')
        main_layout.addWidget(self.delete_temp_btn, stretch=0)

        # >>  CALIBRATION TABLE
        self.table = qtw.QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(['Sensor','Celcius', 'Time'])
        main_layout.addWidget(self.table, stretch=3)

        # >>  CALIBRATION TEMPERATURE INPUT
        calib_widget = qtw.QWidget()
        calib_input_layout = qtw.QHBoxLayout(calib_widget)

        self.user_temp = qtw.QLineEdit()
        calib_input_layout.addWidget(self.user_temp, stretch=1)

        self.add_temp_btn = qtw.QPushButton('Enter')

        calib_input_layout.addWidget(self.add_temp_btn, stretch=0)
        main_layout.addWidget(calib_widget, stretch=0)

class CalibInput(qtw.QWidget):
    temp_added = Signal()

    def __init__(self, module):
        super(CalibInput, self).__init__()

        self.module = module

        #to check if there is data yet for calibration
        self.have_data_for_calib = False
        
        main_layout = qtw.QHBoxLayout(self)

        self.OhmTempPlot = pg.PlotWidget(title="Ohms Vs Celcius", background="#f5f5f5")
        self.OhmTempPlotLegend = self.OhmTempPlot.addLegend()
        self.OhmTempPlot.showGrid(x=True, y=True)
        self.OhmTempPlot.setLabel('left', 'Resistance (Ohms)')  # Y-axis label
        self.OhmTempPlot.setLabel('bottom', f'Celcius ({u"\N{DEGREE SIGN}"}C)')  # X-axis label
        self.ohm_temp_plots = {}
        for channel, sensor in self.module.sensors.items():
            self.ohm_temp_plots[channel] = self.OhmTempPlot.plot(
                [], [], 
                #pen=self.module.color_map[channel], 
                name=sensor.name,
                symbol="+",
                symbolBrush=self.module.color_map[channel]
            )

        main_layout.addWidget(self.OhmTempPlot, stretch=1)
        
        self.calib_widget = CalibWidget()
        main_layout.addWidget(self.calib_widget, stretch=0)

        self.calib_widget.delete_temp_btn.clicked.connect(self.delete_selected_row)
        self.calib_widget.add_temp_btn.clicked.connect(self.update_data)

        # >>  self Signals
        self.temp_added.connect(self.update_table)
        self.temp_added.connect(self.update_temp_ohm_plot)

    @Slot()
    def update_data(self):
        #add check if module has data yet
        self.have_data_for_calib = all([sensor.raw_adcs for sensor in self.module.sensors.values()])
        if (T := self.calib_widget.user_temp.text()) and self.have_data_for_calib and is_float(T):
            for sensor in self.module.sensors.values():
                sensor.calib_data['temps'].append(float(T))
                sensor.calib_data['ohms'].append(sensor.ohms[-1])

                sensor.calib_data['raw_adcs'].append(sensor.raw_adcs[-1])
                sensor.calib_data['times'].append(sensor.times[-1])
            self.temp_added.emit()
        elif not self.have_data_for_calib:
            print("All enabled sensors do not have calibration yet. Or temperature could not be converted to float")
            self.calib_widget.user_temp.clear()  
    @Slot()
    def update_table(self):
        # Find the next available row in the table
        for sensor in self.module.sensors.values():
            time = sensor.calib_data['times'][-1]
            temp = sensor.calib_data['temps'][-1]

            row_position = self.calib_widget.table.rowCount()
            self.calib_widget.table.insertRow(row_position)

            time_item = qtw.QTableWidgetItem(f"{time.hour}:{str(time.minute).zfill(2)}")
            time_item.setFlags(time_item.flags() & ~Qt.ItemIsEditable)
            self.calib_widget.table.setItem(row_position, 0, qtw.QTableWidgetItem(sensor.name))
            self.calib_widget.table.setItem(row_position, 1, qtw.QTableWidgetItem(str(temp)))
            self.calib_widget.table.setItem(row_position, 2, time_item)

        # Clear the input field
        self.calib_widget.user_temp.clear()   
    
    @Slot()
    def update_temp_ohm_plot(self) -> None:
        for channel, sensor in self.module.sensors.items():
            self.ohm_temp_plots[channel].setData(sensor.calib_data['temps'], sensor.calib_data['ohms'])

    def delete_selected_row(self):
        # Get the selected row
        selected_row = self.calib_widget.table.currentRow()
        # Remove the selected row if there is a selection
        if selected_row != -1:
            self.calib_widget.table.removeRow(selected_row)