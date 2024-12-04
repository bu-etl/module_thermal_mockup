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

PATH_OF_SCRIPT:str =  os.path.dirname(os.path.abspath(__file__))

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
    
#=============== Widgets ===============#

#------ Dropdown Widget from online------#
"""
This is not my code, found online at this repository:
https://github.com/EsoCoding/PySide6-Collapsible-Widget
"""
class Header(qtw.QWidget):
    """Header class for collapsible group"""
    def __init__(self, name, content_widget):
        """Header Class Constructor to initialize the object.
        Args:
            name (str): Name for the header
            content_widget (QtWidgets.QWidget): Widget containing child elements
        """
        super(Header, self).__init__()
        self.content = content_widget

        self.expand_icon_path = os.path.join(PATH_OF_SCRIPT, "icons/caret-down-fill.svg")
        self.collapse_icon_path = os.path.join(PATH_OF_SCRIPT, "icons/caret-right-fill.svg")

        self.setSizePolicy(qtw.QSizePolicy.Expanding,
                           qtw.QSizePolicy.Fixed)

        # Create a stacked layout to hold the background and widget
        stacked = qtw.QStackedLayout(self)
        stacked.setStackingMode(qtw.QStackedLayout.StackAll)
        # Create a background label with a specific style sheet
        background = qtw.QLabel()
        background.setStyleSheet(
            "QLabel{ background-color: rgb(93, 93, 93); padding-top: -20px; border-radius:2px}")

        # Create a widget and a layout to hold the icon and label
        widget = qtw.QWidget()
        layout = qtw.QHBoxLayout(widget)

        # Create an icon label and set its text and style sheet
        # self.icon = QLabel()
        # self.icon.setText(self.expand_ico)
        # self.icon.setStyleSheet(
        #     "QLabel { font-weight: bold; font-size: 20px; color: #000000 }")
        
        self.icon = QSvgWidget(self.expand_icon_path)
        self.icon.setFixedSize(20, 20)  # Adjust size as needed
        
        layout.addWidget(self.icon)

        # Add the icon and the label to the layout and set margins
        layout.addWidget(self.icon)
        layout.addWidget(self.icon)
        layout.setContentsMargins(11, 0, 11, 0)

        # Create a font and a label for the header name
        font = QFont()
        font.setBold(True)
        label = qtw.QLabel(name)
        label.setStyleSheet("QLabel { margin-top: 5px; }")
        label.setFont(font)

        # Add the label to the layout and add a spacer for expanding
        layout.addWidget(label)
        layout.addItem(qtw.QSpacerItem(
            0, 0, qtw.QSizePolicy.Expanding, qtw.QSizePolicy.Expanding))

        # Add the widget and the background to the stacked layout
        stacked.addWidget(widget)
        stacked.addWidget(background)
        # Set the minimum height of the background based on the layout height
        background.setMinimumHeight(layout.sizeHint().height() * 1.5)

    def mousePressEvent(self, *args):
        """Handle mouse events, call the function to toggle groups"""
        # Toggle between expand and collapse based on the visibility of the content widget
        self.expand() if not self.content.isVisible() else self.collapse()

    def expand(self):
        """Expand the collapsible group"""
        self.content.setVisible(True)
        # self.icon.setText(self.collapse_ico)  # Set text instead of pixmap
        self.icon.load(self.expand_icon_path)

    def collapse(self):
        """Collapse the collapsible group"""
        self.content.setVisible(False)
        # self.icon.setText(self.expand_ico)
        self.icon.load(self.collapse_icon_path)

class Container(qtw.QWidget):
    """Class for creating a collapsible group similar to how it is implement in Maya"""
    def __init__(self, name, color_background=False):
            """Container Class Constructor to initialize the object
            Args:
                name (str): Name for the header
                color_background (bool): whether or not to color the background lighter like in maya
            """
            super(Container, self).__init__() # Call the constructor of the parent class
    
            layout = qtw.QVBoxLayout(self) # Create a QVBoxLayout instance and pass the current object as the parent
            layout.setContentsMargins(0, 0, 0, 0) # Set the margins of the layout to 0
    
            self._content_widget = qtw.QWidget() # Create a QWidget instance and assign it to the instance variable _content_widget
    
            if color_background:
                # If color_background is True, set the stylesheet of _content_widget to have a lighter background color
                self._content_widget.setStyleSheet(".QWidget{background-color: rgb(73, 73, 73); "
                                                   "margin-left: 2px; padding-top: 20px; margin-right: 2px}")
    
            header = Header(name, self._content_widget) # Create a Header instance and pass the name and _content_widget as arguments
            layout.addWidget(header) # Add the header to the layout
            layout.addWidget(self._content_widget) # Add the _content_widget to the layout
    
            # assign header methods to instance attributes so they can be called outside of this class
            self.collapse = header.collapse # Assign the collapse method of the header to the instance attribute collapse
            self.expand = header.expand # Assign the expand method of the header to the instance attribute expand
            self.toggle = header.mousePressEvent # Assign the mousePressEvent method of the header to the instance attribute toggle
    
    @property
    def contentWidget(self):
            """Getter for the content widget
    
            Returns: Content widget
            """
            return self._content_widget # Return the _content_widget when the contentWidget property is accessed

#---------------------------------------#

# -------- My Run Config Widget --------#
def run_config_preview(db_session, run_config: RunConfig) -> qtw.QWidget:
    # run info preview

    # picture preview

    # module preview

    #----> lets just start by dumping to a text box

    display = qtw.QPlainTextEdit()
    display.setReadOnly(True)

    display.appendPlainText(str(run_config))
    return display


class RunConfigDropdown(qtw.QWidget):
    def __init__(self, db_session):
        super(RunConfigDropdown, self).__init__()

        self.session = db_session

        main_layout = qtw.QVBoxLayout(self)
        container = Container("Run Configuration", color_background=True)
        main_layout.addWidget(container)

        self.container_layout = qtw.QGridLayout(container.contentWidget)
        self.config_file_btn = qtw.QPushButton("Select Config File")
        self.config_file_btn.clicked.connect(self.load_run_config)
        self.container_layout.addWidget(self.config_file_btn)

    @Slot()
    def load_run_config(self):
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
                run_config = RunConfig.model_validate(tomllib.load(f))
            except ValidationError as e:
                self.raise_crit_message('Run Config File Error', str(e))

        self.run = None
        if run_config.reuse_run_id is not None:
            self.run = self.query_run(run_config.reuse_run_id)
        else:
            cold_plate = self.query_cold_plate(run_config.cold_plate)
            if cold_plate is not None:
                self.run = dm.Run(
                    cold_plate = cold_plate,
                    mode = run_config.mode,
                    comment = run_config.comment
                )
                self.session.add(self.run)
                print("COMMITTED TO DB!!")
                #self.session.commit()
        if self.run is not None:
            self.modules = [self.query_module(mod_sn) for mod_sn in run_config.modules]
            self.load_run_info(self.run)
            self.load_modules(run_config.modules)
            self.load_image(self.run)
        
    def load_run_info(self, run: dm.Run):
        # Centered put the Run ID = ... then mode then comment
        run_info = qtw.QGroupBox("Run Info")
        run_info_layout = qtw.QVBoxLayout(run_info)
        run_info_layout.setAlignment(Qt.AlignCenter)
        run_info_layout.addWidget(qtw.QLabel(f"Run ID = {run.id}"))
        run_info_layout.addWidget(qtw.QLabel(f"Mode: {run.mode}"))
        run_info_layout.addWidget(qtw.QLabel(f"Comment: {run.comment}"))
        self.container_layout.addWidget(run_info)
      
    def load_modules(self, modules:list[ModuleConfig]):
        # make a small square that contains the module serial number and plate position
        # for each module put it side by side
        db_modules = [self.query_module(mod.serial_number) for mod in modules]
        if None not in db_modules:
            for i, module in enumerate(modules):
                module_info = qtw.QGroupBox(f"Module {i+1}")
                module_info_layout = qtw.QVBoxLayout(module_info)
                module_info_layout.setAlignment(Qt.AlignCenter)
                module_info_layout.addWidget(qtw.QLabel(f"Serial Number: {module.serial_number}"))
                module_info_layout.addWidget(qtw.QLabel(f"Plate Position: {module.cold_plate_position}"))
                self.container_layout.addWidget(module_info)

    def load_image(self, run) -> None:
        pixmap = QPixmap()
        pixmap.loadFromData(run.cold_plate.plate_image)
        
        label = qtw.QLabel()
        label.setPixmap(pixmap)
        label.setScaledContents(True)  # Scale the image to fit the label size

        # Add the label to your layout or display it as needed
        self.container_layout.addWidget(label)


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