from typing import List
from typing import Optional
from sqlalchemy import ForeignKey
from sqlalchemy import String, Integer, Float, DateTime
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import mapped_column, relationship, Mapped, DeclarativeBase
from sqlalchemy.types import LargeBinary
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

    def __repr__(self) -> str:
        return f"ControlBoard(id={self.id!r}, name={self.name!r})"

class Module(Base):
    __tablename__ = "module"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    calibration_id: Mapped[int] = mapped_column(ForeignKey("calibration.id"), nullable=False)

    data: Mapped[List["Data"]] = relationship(back_populates="module")
    def __repr__(self) -> str:
        return f"Module(id={self.id!r}, name={self.name!r})"

class Data(Base):
    __tablename__ = "data"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("run.id"), nullable=False)
    control_board_id: Mapped[int] = mapped_column(ForeignKey("control_board.id"), nullable=True)
    control_board_position: Mapped[int] = mapped_column(Integer, nullable=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("module.id"))
    plate_position: Mapped[int] = mapped_column(Integer, nullable=False)

    sensor: Mapped[str] = mapped_column(String(50))
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    raw_adc: Mapped[str] = mapped_column(String(50))
    volts: Mapped[float] = mapped_column(Float)
    ohms: Mapped[float] = mapped_column(Float) 
    celcius: Mapped[float] = mapped_column(Float)

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
    cold_plate: Mapped[int] = mapped_column(ForeignKey("cold_plate.id"), nullable=True)
    
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

class SensorCalibration(Base):
    __tablename__ = "calibration"
    id: Mapped[int] = mapped_column(primary_key=True)

    module_id: Mapped[int] = mapped_column(ForeignKey("module.id"), nullable=False)
    sensor: Mapped[str] = mapped_column(String(50), nullable=False) 
    fit_ohms_over_celcius: Mapped[float] = mapped_column(Float, nullable=False)
    fit_ohms_intercept: Mapped[float] = mapped_column(Float, nullable=False)

    celcius: Mapped[ARRAY[float]] = mapped_column(ARRAY(Float), nullable=False)
    ohms: Mapped[ARRAY[float]] = mapped_column(ARRAY(Float), nullable=False)
    raw_adc: Mapped[ARRAY[str]] = mapped_column(ARRAY(String(50)), nullable=False)
    times: Mapped[ARRAY[DateTime]] = mapped_column(ARRAY(DateTime), nullable=False)

    module: Mapped["Module"] = relationship(back_populates="calibration")
