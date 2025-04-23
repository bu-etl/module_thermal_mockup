from pydantic import BaseModel, PositiveInt, Field, field_validator, model_validator, ConfigDict
from typing import Literal, Optional, Any, Self
from PySide6 import QtWidgets as qtw
from PySide6.QtCore import Slot, Qt
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtSvgWidgets import QSvgWidget
import tomllib
from pydantic import ValidationError
from pathlib import Path
import database.models as dm
from sqlalchemy import select
from sqlalchemy.orm import Session
from itertools import zip_longest
from firmware_interface import available_firmwares
from functools import partial

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

class DBBase:
    @classmethod
    def set_session(cls, session: Session):
        cls.session = session
    
    @classmethod
    def exists_validator(cls, value, db_model, column, expecting_type=str):
        if isinstance(value, expecting_type):
            # Query for module
            obj = cls.session.execute(
                select(db_model).where(column == value)
            ).scalar()

            assert obj is not None, f"For {db_model.__name__}, this value: {value}, was not found in database"
            return obj
        return value
    
class CaseInsensitiveModel(BaseModel, DBBase):
    @model_validator(mode="before")
    def __lowercase_property_keys__(cls, values: Any) -> Any:
        def __lower__(value: Any) -> Any:
            if isinstance(value, dict):
                return {k.lower():v for k, v in value.items()}
            return value
        return __lower__(values)

class ModuleConfig(CaseInsensitiveModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    module: dm.Module
    cold_plate_position: int
    orientation: Optional[Literal['up', 'down']] = None
    control_board: Optional[dm.ControlBoard] = None
    control_board_position: Optional[Literal['A', 'B', 'C', 'D']] = None
    disabled_sensors: list[Literal['E1', 'E2', 'E3', 'E4', 'L1', 'L2', 'L3', 'L4', 'P1', "P2", "P3"]] = []
    reference_resistors: dict[int, float]

    _lowercase_orientation = field_validator('orientation', mode='before')(lower_validator)
    _module_exists_validator = field_validator('module', mode='before')(
        partial(DBBase.exists_validator, db_model=dm.Module, column=dm.Module.name)
    )
    _control_board_validator = field_validator('control_board', mode='before')(
        partial(DBBase.exists_validator, db_model=dm.ControlBoard, column=dm.ControlBoard.name)
    )

class MicroControllerConfig(CaseInsensitiveModel):
    firmware_version: Literal[*AVAILABLE_FIRMWARES]
    port: str

class Runfig(CaseInsensitiveModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    run: Optional[dm.Run]                = None
    mode: Optional[str]                  = None
    cold_plate: Optional[dm.ColdPlate]   = None
    comment: Optional[str]               = None 

    _uppercase_mode = field_validator('mode', mode='before')(upper_validator)

    @model_validator(mode='before')
    @classmethod
    def validate_run(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # case insensitve keys...
            data = {key.lower(): value for key, value in data.items()}

            reuse_run_given = data.get('run') is not None
            new_config_fields_given = (data.get('mode') is not None or 
                                       data.get('cold_plate') is not None or 
                                       data.get('comment') is not None)
            run_id = data.get('run')
            if reuse_run_given and new_config_fields_given:
                raise ValueError("You gave an old run to work from and the fields to make a new new run. Please only give the run id for using an old run or the others for a new run.")
            elif reuse_run_given:
                run = DBBase.exists_validator(run_id, dm.Run, dm.Run.id, expecting_type=int)
                data['run'] = run
            elif new_config_fields_given:
                cold_plate = DBBase.exists_validator(data['cold_plate'], dm.ColdPlate, dm.ColdPlate.name)
                run = dm.Run(
                    mode=data['mode'],
                    comment=data['comment'],
                    cold_plate = cold_plate
                )
                cls.session.add(run)
                data['cold_plate'] = cold_plate
                data['run'] = run
            else:
                raise ValueError("Invalid Run Configuration, if you are making a new run make sure you give the mode, cold_plate and comment")
        return data
    
class RunConfig(CaseInsensitiveModel):
    Run: Runfig = Field(validation_alias='run') #gotta do this alias becuase of the case insensitivity change...
    Microcontroller: MicroControllerConfig = Field(validation_alias='microcontroller')
    Modules: list[ModuleConfig] = Field(validation_alias="modules")

    @field_validator('Modules',mode='after')
    @classmethod
    def multi_module_need_control_board(cls, module_configs: list[ModuleConfig]):
        assert len(module_configs) > 0, "At least one module must be provided."
        if len(module_configs) > 1:
            control_boards = []
            control_board_positions = []
            for mod_config in module_configs:
                assert mod_config.control_board is not None, f"Please provide the control board used for this module ({mod_config.module.name}) in this multi module setup"
                assert mod_config.control_board_position is not None, f"Please provide the position on the control board for this module ({mod_config.module.name}) in this multi module setup"
                control_boards.append(mod_config.control_board)
                control_board_positions.append(mod_config.control_board_position)
            assert len(control_boards) == 1, f"You have selected multiple control boards when the software only supports one"
            assert len(control_board_positions) == len(set(control_board_positions)), "Not all control board positions are unique!"
        return module_configs

#=============== Widgets ===============#

class RunConfigModal(qtw.QDialog):
    def __init__(self, db_session):
        super(RunConfigModal, self).__init__()

        self.session = db_session
        DBBase.set_session(self.session)

        self.run_config: RunConfig = None
        #self.db_data: dict = None
        self.setWindowTitle("Set Run Configuration")

        self.main_layout = qtw.QVBoxLayout(self)

        self.config_file_btn = qtw.QPushButton("Select Config File")
        self.config_file_btn.clicked.connect(self.select_config_file)
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


        current_file_dir = Path(__file__).resolve().parent
        default_config = current_file_dir.parent / "config.toml"
        if default_config.is_file():
            self.load_config(str(default_config))

    @Slot()
    def select_config_file(self) -> None:
        file_path, _ = qtw.QFileDialog.getOpenFileName(
            self, 
            "Select Config File", 
            None,
            "TOML (*.toml)"
        )
        if not file_path:
            # then they exited without selecing file
            return None
        self.load_config(file_path)

    def load_config(self, file_path: str):
        if not file_path:
            # then they exited without selecing file
            return None
        try:
            with open(file_path, 'rb') as f:
                self.run_config = RunConfig.model_validate(tomllib.load(f))
            self.add_run_visual(self.run_config.Run.run)
            self.add_microcontroller_visual(self.run_config.Microcontroller)
            self.add_modules_visual(self.run_config.Modules)
            self.add_image_visual(self.run_config.Run.run)
        except ValidationError as error:
            print(error)
            self.raise_crit_message("Config Failure", str(str([e['msg'] for e in error.errors()])))
  
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
            for j, module_config in enumerate(row):
                if module_config is None:
                    continue
                module_info = qtw.QGroupBox(f"Module {n_cols*i+j+1}")
                module_info_layout = qtw.QVBoxLayout(module_info)
                module_info_layout.setAlignment(Qt.AlignCenter)
                module_info_layout.addWidget(qtw.QLabel(f"Serial Number: {module_config.module.name}"))
                module_info_layout.addWidget(qtw.QLabel(f"Plate Position: {module_config.cold_plate_position}"))
                module_info_layout.addWidget(qtw.QLabel(f"Orientation: {module_config.orientation}"))
                module_info_layout.addWidget(qtw.QLabel(f"Disabled Sensors: {module_config.disabled_sensors}"))
                module_info_layout.addWidget(qtw.QLabel(f"Control Board: {module_config.control_board}"))
                module_info_layout.addWidget(qtw.QLabel(f"Control Board Position: {module_config.control_board_position}"))

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

    def raise_crit_message(self, name: str, error_message: str) -> None:
        qtw.QMessageBox.critical(
            self,
            name,
            error_message,
            buttons=qtw.QMessageBox.Retry,
            defaultButton=qtw.QMessageBox.Retry,
        )


#====================================#