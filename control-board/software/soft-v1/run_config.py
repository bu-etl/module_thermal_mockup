from pydantic import BaseModel, PositiveInt, Field, field_validator, model_validator
from typing import Literal, Optional, Any, Self
from PySide6 import QtWidgets as qtw
from PySide6.QtCore import Slot, Qt
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtSvgWidgets import QSvgWidget
import tomllib
from pydantic import ValidationError
import os
import database.models as dm
from sqlalchemy import select
from itertools import zip_longest
from firmware_interface import available_firmwares

PATH_OF_SCRIPT:str =  os.path.dirname(os.path.abspath(__file__))
AVAILABLE_FIRMWARES:list[str] = available_firmwares()

def gridded_list(array: list, n_cols: int) -> list[tuple]:
    """
    Reshape a list into n_cols * n array with Nones padded 
    https://stackoverflow.com/questions/57645094/reshaping-python-array-for-unknown-rows-using-1-filling-remaining-spaces-with
    """
    return list(zip_longest(*[iter(array)] * n_cols))

class ConfigFailureError(Exception):
    pass

# ----------------------- PYDANTIC MODELS ------------------------------#
#GUI for control board
def lower_validator(value: str) -> str:
    return value.lower() if isinstance(value, str) else value
def upper_validator(value: str) -> str:
    return value.upper() if isinstance(value, str) else value

class CaseInsensitiveModel(BaseModel):
    @model_validator(mode="before")
    def __lowercase_property_keys__(cls, values: Any) -> Any:
        def __lower__(value: Any) -> Any:
            if isinstance(value, dict):
                return {k.lower():v for k, v in value.items()}
            return value
        return __lower__(values)

class ModuleConfig(CaseInsensitiveModel):
    serial_number: str
    cold_plate_position: int
    orientation: Optional[Literal['up', 'down']] = None
    control_board: Optional[str] = None
    control_board_position: Optional[Literal['A', 'B', 'C', 'D']] = None
    disabled_sensors: list[Literal['E1', 'E2', 'E3', 'E4', 'L1', 'L2', 'L3', 'L4']] = []

    _lowercase_orientation = field_validator('orientation', mode='before')(lower_validator)

class MicroControllerConfig(CaseInsensitiveModel):
    firmware_version: Literal[*AVAILABLE_FIRMWARES]
    port: str

class Run(CaseInsensitiveModel):
    reuse_run_id: Optional[PositiveInt]  = None
    mode: Optional[str]                  = None
    cold_plate: Optional[str]            = None
    comment: Optional[str]               = None 

    _uppercase_mode = field_validator('mode', mode='before')(upper_validator)

    @model_validator(mode='after')
    def new_or_old_run_fields(self) -> Self:
        reuse_run_id_given = self.reuse_run_id is not None
        new_config_fields_given = self.mode is not None or self.cold_plate is not None or self.comment is not None
        assert (
            (reuse_run_id_given and not new_config_fields_given) or
            (not reuse_run_id_given and new_config_fields_given)
        ), "Invalid configuration: either reuse_run_id should be specified with no other keys, or mode and cold_plate should be specified without reuse_run_id."
        return self

class RunConfig(CaseInsensitiveModel):
    save_location: Literal["local", "database"] = "database" 
    run: Run
    microcontroller: MicroControllerConfig
    modules: list[ModuleConfig]

    @field_validator('modules',mode='after')
    @classmethod
    def multi_module_need_control_board(cls, v: list[ModuleConfig]):
        assert len(v) > 0, "At least one module must be provided."
        if len(v) > 1:
            control_boards = []
            control_board_positions = []
            for mod in v:
                assert mod.control_board is not None, f"Please provide the control board used for this module ({mod.serial_number}) in this multi module setup"
                assert mod.control_board_position is not None, f"Please provide the position on the control board for this module ({mod.serial_number}) in this multi module setup"
                control_boards.append(mod.control_board)
                control_board_positions.append(mod.control_board_position)
            assert len(control_boards) == 1, f"You have selected multiple control boards when the software only supports one"
            assert len(control_board_positions) == len(set(control_board_positions)), "Not all control board positions are unique!"
        return v

#=============== Widgets ===============#

class RunConfigModal(qtw.QDialog):
    def __init__(self, db_session):
        super(RunConfigModal, self).__init__()

        self.session = db_session
        self.run_config: RunConfig = None
        self.db_data: dict = None
        self.setWindowTitle("Set Run Configuration")

        self.main_layout = qtw.QVBoxLayout(self)

        self.config_file_btn = qtw.QPushButton("Select Config File")
        self.config_file_btn.clicked.connect(self.load_run_config)
        self.main_layout.addWidget(self.config_file_btn)

        self.config_preview = qtw.QWidget()
        self.config_preview_layout = qtw.QVBoxLayout()

        self.config_preview.setLayout(self.config_preview_layout)
        self.main_layout.addWidget(self.config_preview)
        
        QBtn = (
            qtw.QDialogButtonBox.Ok | qtw.QDialogButtonBox.Cancel
        )
        self.buttonBox = qtw.QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.main_layout.addWidget(self.buttonBox)

    @Slot()
    def load_run_config(self) -> None:
        file_path, _ = qtw.QFileDialog.getOpenFileName(
            self, 
            "Select Config File", 
            None,
            "TOML (*.toml)"
        )
        if not file_path:
            # then they exited without selecing file
            return None
        try:
            self.run_config = self.run_config_from_file(file_path)
            self.db_data = self.load_db_data(self.run_config)
            self.add_run_visual(self.db_data["run"])
            self.add_microcontroller_visual(self.run_config.microcontroller)
            self.add_modules_visual(self.run_config.modules)
            self.add_image_visual(self.db_data["run"])
        except ConfigFailureError as e:
            print(e, type(e))
            self.raise_crit_message("Config Failure", str(e))

    def run_config_from_file(self, file_path: str) -> None | RunConfig:
        # get pydantic run config
        with open(file_path, 'rb') as f:
            try:
                return RunConfig.model_validate(tomllib.load(f))
            except ValidationError as error:
                raise ConfigFailureError(str([e['msg'] for e in error.errors()]))

    def load_db_data(self, run_config: RunConfig) -> dict:
        #------------- LOAD MODULES -----------------#
        modules = []
        for mod in run_config.modules:
            module = self.query_module(mod.serial_number)
            if module is None:
                raise ConfigFailureError(f"The module ({mod.serial_number}) does not exist in the database")
            modules.append(module)
        #--------------------------------------------#

        #------------- LOAD CONTROL BOARD -----------------#
        control_board_name = self.run_config.modules[0].control_board # validated in pydantic that all are the same name
        if control_board_name is None and len(modules) > 1:
            raise ConfigFailureError(f"This control board name was not found in this multi board setup, {control_board_name}")
        
        control_board = self.query_control_board(control_board_name) 
        if control_board is not None:
            raise ConfigFailureError(f"The control board ({control_board_name}) does not exist in the database")

        #------------- LOAD RUN -----------------#
        if run_config.run.reuse_run_id is not None:
            run = self.query_run(run_config.run.reuse_run_id)
            if run is None:
                raise ConfigFailureError(f"The run ({run_config.run.reuse_run_id}) does not exist in the database")
            
            cold_plate = run.cold_plate
        else:
            # should make a modal asking are you sure you would like to start a new run?
            run = dm.Run(
                cold_plate = cold_plate,
                mode = run_config.run.mode,
                comment = run_config.run.comment
            )
            self.session.add(run)  

            #------------- LOAD COLD PLATE -----------------#
            cold_plate = self.query_cold_plate(run_config.run.cold_plate)
            if cold_plate is None:
                raise ConfigFailureError(f"The cold plate ({run_config.run.cold_plate}) does not exist in the database")

        return {
            'run': run,
            'modules': modules,
            'cold_plate': cold_plate,
            'control_board': control_board,
        }
    
    def add_run_visual(self, run: dm.Run) -> None:
        # Centered put the Run ID = ... then mode then comment
        run_info = qtw.QGroupBox("Run Info")
        run_info_layout = qtw.QVBoxLayout(run_info)
        run_info_layout.setAlignment(Qt.AlignCenter)
        run_info_layout.addWidget(qtw.QLabel(f"Run ID = {run.id if run.id else 'NEW RUN'}"))
        run_info_layout.addWidget(qtw.QLabel(f"Mode: {run.mode}"))
        run_info_layout.addWidget(qtw.QLabel(f"Comment: {run.comment}"))
        self.config_preview_layout.addWidget(run_info)

    def add_microcontroller_visual(self, microcontroller_config: MicroControllerConfig) -> None:
        # Centered put the Run ID = ... then mode then comment
        run_info = qtw.QGroupBox("Microcontroller Config")
        run_info_layout = qtw.QVBoxLayout(run_info)
        run_info_layout.setAlignment(Qt.AlignCenter)
        run_info_layout.addWidget(qtw.QLabel(f"Firmware: {microcontroller_config.firmware_version}"))
        run_info_layout.addWidget(qtw.QLabel(f"Port: {microcontroller_config.port}"))

        self.config_preview_layout.addWidget(run_info)
    
    def add_modules_visual(self, modules:list[ModuleConfig]) -> None:
        # make a small square that contains the module serial number and plate position
        # for each module put it side by side
        modules_layout = qtw.QGridLayout()
        modules_widget = qtw.QWidget()

        # lets do 5 * n size grid
        n_cols = 5
        modules = gridded_list(modules, n_cols)

        for i, row in enumerate(modules):
            for j, module in enumerate(row):
                if module is None:
                    continue
                module_info = qtw.QGroupBox(f"Module {n_cols*i+j+1}")
                module_info_layout = qtw.QVBoxLayout(module_info)
                module_info_layout.setAlignment(Qt.AlignCenter)
                module_info_layout.addWidget(qtw.QLabel(f"Serial Number: {module.serial_number}"))
                module_info_layout.addWidget(qtw.QLabel(f"Plate Position: {module.cold_plate_position}"))
                module_info_layout.addWidget(qtw.QLabel(f"Orientation: {module.orientation}"))
                module_info_layout.addWidget(qtw.QLabel(f"Disabled Sensors: {module.disabled_sensors}"))

                module_info_layout.addWidget(qtw.QLabel(f"Control Board: {module.control_board}"))
                module_info_layout.addWidget(qtw.QLabel(f"Control Board Position: {module.control_board_position}"))

                modules_layout.addWidget(module_info, i, j)

        modules_widget.setLayout(modules_layout)
        self.config_preview_layout.addWidget(modules_widget)

    def add_image_visual(self, run) -> None:
        pixmap = QPixmap()
        pixmap.loadFromData(run.cold_plate.plate_image)
        
        label = qtw.QLabel()
        label.setPixmap(pixmap)
        label.setScaledContents(True)  # Scale the image to fit the label size

        # Add the label to your layout or display it as needed
        self.config_preview_layout.addWidget(label)

    def query_run(self, run_id: int) -> dm.Run | None:
        run = self.session.execute(
            select(dm.Run).where(
                dm.Run.id == run_id
            )
        ).scalar_one_or_none()
        return run

    def query_cold_plate(self, name: str) -> dm.ColdPlate | None:
        cold_plate = self.session.execute(
            select(dm.ColdPlate).where(
                dm.ColdPlate.name == name
            )
        ).scalar_one_or_none()
        return cold_plate
    
    def query_control_board(self, name: str) -> dm.ControlBoard | None:
        control_board = self.session.execute(
            select(dm.ControlBoard).where(
                dm.ControlBoard.name == name
            )
        ).scalar_one_or_none()
        return control_board

    def query_module(self, serial_number: str) -> dm.Module | None:
        module = self.session.execute(
            select(dm.Module).where(
                dm.Module.name == serial_number
            )
        ).scalar_one_or_none()
        return module
    
    def raise_crit_message(self, name: str, error_message: str) -> None:
        qtw.QMessageBox.critical(
            self,
            name,
            error_message,
            buttons=qtw.QMessageBox.Retry,
            defaultButton=qtw.QMessageBox.Retry,
        )


#====================================#