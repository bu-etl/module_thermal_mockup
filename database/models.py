from typing import List
from typing import Optional
from sqlalchemy import ForeignKey
from sqlalchemy import String, Integer, Float, DateTime
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import mapped_column, relationship, Mapped, DeclarativeBase
from sqlalchemy.types import LargeBinary
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime

def create_all(engine) -> None:
    """
    Creates all databse tables and relationships
    """
    Base.metadata.create_all(engine)

class Base(DeclarativeBase):
    pass

class ControlBoard(Base):
    __tablename__ = "control_board"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    data: Mapped[List["Data"]] = relationship(back_populates="control_board")

    def __repr__(self) -> str:
        return f"ControlBoard(id={self.id!r}, name={self.name!r})"

class Module(Base):
    __tablename__ = "module"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    calibration_id: Mapped[int] = mapped_column(ForeignKey("module_calibration.id"), nullable=True) # MAKE FALSE
    
    calibration: Mapped["ModuleCalibration"] = relationship(back_populates="module")
    data: Mapped[List["Data"]] = relationship(back_populates="module")

    all_calibrations: Mapped[List["SensorCalibration"]] = relationship(back_populates="module")
    
    def __repr__(self) -> str:
        return f"Module(id={self.id!r}, name={self.name!r})"

class Data(Base):
    __tablename__ = "data"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("run.id"), nullable=False)
    control_board_id: Mapped[int] = mapped_column(ForeignKey("control_board.id"), nullable=True)
    control_board_position: Mapped[int] = mapped_column(Integer, nullable=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("module.id"))
    module_orientation: Mapped[str] = mapped_column(String(50), nullable=True) # MAKE FALSE ===# up or down, relative to the beam pipe
    plate_position: Mapped[int] = mapped_column(Integer, nullable=True) # MAKE FALSE AFTER ===# 1, 2, 3, 4, etc...

    sensor: Mapped[str] = mapped_column(String(50))
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    raw_adc: Mapped[str] = mapped_column(String(50))
    celcius: Mapped[float] = mapped_column(Float)

    @hybrid_property
    def volts(self) -> float:
        num = int(str(self.raw_adc)[:-2], 16)
        return 2.5 + (num / 2**15 - 1) * 1.024 * 2.5 / 1

    @hybrid_property
    def ohms(self) -> float:
        return 1E3 / (5 / self.volts_calc - 1)
    
    @hybrid_property
    def celcius_calc(self) -> float:
        return (self.ohms_calc - self.module.calibration.fit_ohms_intercept) / self.module.calibration.fit_ohms_over_celcius
    
    module: Mapped["Module"] = relationship(back_populates="data")
    run: Mapped["Run"] = relationship(back_populates="data")
    control_board: Mapped["ControlBoard"] = relationship(back_populates="data")

    def __repr__(self) -> str:
        return f"Data(id={self.id!r}, module_id={self.module_id!r}, sensor={self.sensor!r}, timestamp={self.timestamp!r}, raw_adc={self.raw_adc!r}, voltage={self.volts!r}, resistance={self.ohms!r}, temperature={self.celcius!r})"
    
class Run(Base):
    __tablename__ = "run"
    id: Mapped[int] = mapped_column(primary_key=True)
    mode: Mapped[str] = mapped_column(String(50), nullable=False, unique=False)
    comment: Mapped[str] =  mapped_column(String(500), nullable=True, unique=False)
    cold_plate_id: Mapped[int] = mapped_column(ForeignKey("cold_plate.id"), nullable=True) # MAKE NULLABLE FALSE LATER
    
    cold_plate: Mapped["ColdPlate"] = relationship(back_populates="run")
    data: Mapped[List["Data"]] = relationship(back_populates="run")

    def __repr__(self) -> str:
        return f"Run(id={self.id!r}, mode={self.mode!r}), comment={self.comment!r}"
    
class ColdPlate(Base):
    """
    Defines all the module positions on the plate / wedge / dee etc...
    """
    __tablename__ = "cold_plate"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True) #epoxy plate, solder plate, dee, etc...
    positions: Mapped[JSONB] = mapped_column(JSONB, nullable=True)
    # plate_positions = {
    #     1: "this is the left position, near first inlet pipe, etc...",
    #     2: "middle top position, next to inlet and outlet",
    #     3: "right position, near the outlet pipe",
    #     4: "third row down from top, near the first inlet pipe",
    plate_image: Mapped[LargeBinary] = mapped_column(LargeBinary, nullable=True)

    run: Mapped["Run"] = relationship(back_populates="cold_plate")

    def __repr__(self) -> str:
        return f"ColdPlate(id={self.id!r}, name={self.name!r})"

class SensorCalibration(Base):
    __tablename__ = "sensor_calibration"
    id: Mapped[int] = mapped_column(primary_key=True)

    module_id: Mapped[int] = mapped_column(ForeignKey("module.id"), nullable=False)
    sensor: Mapped[str] = mapped_column(String(50), nullable=False) 
    fit_ohms_over_celcius: Mapped[float] = mapped_column(Float, nullable=False)
    fit_ohms_intercept: Mapped[float] = mapped_column(Float, nullable=False)

    celcius: Mapped[ARRAY[float]] = mapped_column(ARRAY(Float), nullable=True)
    ohms: Mapped[ARRAY[float]] = mapped_column(ARRAY(Float), nullable=True)
    raw_adc: Mapped[ARRAY[str]] = mapped_column(ARRAY(String(50)), nullable=True)
    times: Mapped[ARRAY[DateTime]] = mapped_column(ARRAY(DateTime), nullable=True)
    all_raw_adcs: Mapped[ARRAY[str]] = mapped_column(ARRAY(String(50)), nullable=True)
    all_raw_times: Mapped[ARRAY[DateTime]] = mapped_column(ARRAY(DateTime), nullable=True)

    module: Mapped["Module"] = relationship(back_populates="all_calibrations")

    def __repr__(self) -> str:
        return f"SensorCalibration(id={self.id!r}, module_id={self.module_id!r}, sensor={self.sensor!r}, fit_ohms_over_celcius={self.fit_ohms_over_celcius!r}, fit_ohms_intercept={self.fit_ohms_intercept!r})"

class ModuleCalibration(Base):
    __tablename__ = "module_calibration"
    id: Mapped[int] = mapped_column(primary_key=True)
    comment: Mapped[str] = mapped_column(String(500), nullable=True)

    E1_id: Mapped[int] = mapped_column(ForeignKey("sensor_calibration.id"), nullable=True)
    E2_id: Mapped[int] = mapped_column(ForeignKey("sensor_calibration.id"), nullable=True)
    E3_id: Mapped[int] = mapped_column(ForeignKey("sensor_calibration.id"), nullable=True)
    E4_id: Mapped[int] = mapped_column(ForeignKey("sensor_calibration.id"), nullable=True)

    L1_id: Mapped[int] = mapped_column(ForeignKey("sensor_calibration.id"), nullable=True)
    L2_id: Mapped[int] = mapped_column(ForeignKey("sensor_calibration.id"), nullable=True)
    L3_id: Mapped[int] = mapped_column(ForeignKey("sensor_calibration.id"), nullable=True)
    L4_id: Mapped[int] = mapped_column(ForeignKey("sensor_calibration.id"), nullable=True)

    E1: Mapped["SensorCalibration"] = relationship("SensorCalibration", foreign_keys=[E1_id], post_update=True)
    E2: Mapped["SensorCalibration"] = relationship("SensorCalibration", foreign_keys=[E2_id], post_update=True)
    E3: Mapped["SensorCalibration"] = relationship("SensorCalibration", foreign_keys=[E3_id], post_update=True)
    E4: Mapped["SensorCalibration"] = relationship("SensorCalibration", foreign_keys=[E4_id], post_update=True)
    L1: Mapped["SensorCalibration"] = relationship("SensorCalibration", foreign_keys=[L1_id], post_update=True)
    L2: Mapped["SensorCalibration"] = relationship("SensorCalibration", foreign_keys=[L2_id], post_update=True)
    L3: Mapped["SensorCalibration"] = relationship("SensorCalibration", foreign_keys=[L3_id], post_update=True)
    L4: Mapped["SensorCalibration"] = relationship("SensorCalibration", foreign_keys=[L4_id], post_update=True)

    module: Mapped["Module"] = relationship(back_populates="calibration")   

    def __repr__(self) -> str:
        return f"ModuleCalibration(id={self.id!r}, comment={self.comment!r})"