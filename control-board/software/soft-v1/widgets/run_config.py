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

PATH_OF_SCRIPT:str =  os.path.dirname(os.path.abspath(__file__))

def gridded_list(array: list, n_cols: int) -> list[tuple]:
    """
    Reshape a list into n_cols * n array with Nones padded 
    https://stackoverflow.com/questions/57645094/reshaping-python-array-for-unknown-rows-using-1-filling-remaining-spaces-with
    """
    return list(zip_longest(*[iter(array)] * n_cols))

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
    control_board_position: Optional[int] = Field(None, ge=1, le=4)
    
    _lowercase_orientation = field_validator('orientation', mode='before')(lower_validator)

class RunConfig(CaseInsensitiveModel):
    reuse_run_id: Optional[PositiveInt]  = None
    mode: Optional[str]                  = None
    cold_plate: Optional[str]            = None
    comment: Optional[str]               = None
    modules: list[ModuleConfig]

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
    
    @field_validator('modules',mode='after')
    @classmethod
    def multi_module_need_control_board(cls, v: list[ModuleConfig]):
        assert len(v) > 0, "At least one module must be provided."
        if len(v) > 1:
            for mod in v:
                assert mod.control_board is not None, f"Please provide the control board used for this module ({mod.serial_number}) in this multi module setup"
                assert mod.control_board_position is not None, f"Please provide the position on the control board for this module ({mod.serial_number}) in this multi module setup"
        return v
#=============== Widgets ===============#

class RunConfigModal(qtw.QDialog):
    def __init__(self, db_session):
        super(RunConfigModal, self).__init__()

        self.session = db_session

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
        
        with open(file_path, 'rb') as f:
            try:
                self.run_config = RunConfig.model_validate(tomllib.load(f))
            except ValidationError as error:
                self.raise_crit_message('Run Config File Error', str([e['msg'] for e in error.errors()]))
                return
            
        self.run = None
        if self.run_config.reuse_run_id is not None:
            self.run = self.query_run(self.run_config.reuse_run_id)
        else:
            cold_plate = self.query_cold_plate(self.run_config.cold_plate)
            if cold_plate is not None:
                # should make a modal asking are you sure you would like to start a new run?

                self.run = dm.Run(
                    cold_plate = cold_plate,
                    mode = self.run_config.mode,
                    comment = self.run_config.comment
                )
                self.session.add(self.run)
                
        if self.run is None:
            # if no run then a config error happened
            return
        
        # need no autoflush since we do not commit self.run yet if it is a new run
        with self.session.no_autoflush:
            self.modules = [self.query_module(mod.serial_number) for mod in self.run_config.modules]
            if None in self.modules:
                return
            self.load_run_info(self.run)
            self.load_modules(self.run_config.modules)
            self.load_image(self.run)
        
    def load_run_info(self, run: dm.Run) -> None:
        # Centered put the Run ID = ... then mode then comment
        run_info = qtw.QGroupBox("Run Info")
        run_info_layout = qtw.QVBoxLayout(run_info)
        run_info_layout.setAlignment(Qt.AlignCenter)
        run_info_layout.addWidget(qtw.QLabel(f"Run ID = {run.id if run.id else 'NEW RUN'}"))
        run_info_layout.addWidget(qtw.QLabel(f"Mode: {run.mode}"))
        run_info_layout.addWidget(qtw.QLabel(f"Comment: {run.comment}"))
        self.config_preview_layout.addWidget(run_info)
    
    def load_modules(self, modules:list[ModuleConfig]) -> None:
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
                modules_layout.addWidget(module_info, i, j)

        modules_widget.setLayout(modules_layout)
        self.config_preview_layout.addWidget(modules_widget)

    def load_image(self, run) -> None:
        pixmap = QPixmap()
        pixmap.loadFromData(run.cold_plate.plate_image)
        
        label = qtw.QLabel()
        label.setPixmap(pixmap)
        label.setScaledContents(True)  # Scale the image to fit the label size

        # Add the label to your layout or display it as needed
        self.config_preview_layout.addWidget(label)

    def query_run(self, run_id: int) -> dm.Run:
        run = self.session.execute(
            select(dm.Run).where(
                dm.Run.id == run_id
            )
        ).scalar_one_or_none()

        if run is None:
            self.raise_crit_message(
                "Not In DB Error",
                f"This RUN_ID={run_id} does not exist in the database and thus cannot be loaded"
            )
        return run

    def query_cold_plate(self, name: str):
        cold_plate = self.session.execute(
            select(dm.ColdPlate).where(
                dm.ColdPlate.name == name
            )
        ).scalar_one_or_none()

        if cold_plate is None:
            self.raise_crit_message(
                "Not In DB Error",
                f"The cold plate ({name}) does not exist in the database"
            )
        
        return cold_plate
    
    def query_module(self, serial_number: str):
        module = self.session.execute(
            select(dm.Module).where(
                dm.Module.name == serial_number
            )
        ).scalar_one_or_none()

        if module is None:
            self.raise_crit_message(
                "Not In DB Error",
                f"The module ({serial_number}) does not exist in the database"
            )
        
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