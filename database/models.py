from typing import List
from sqlalchemy import ForeignKey, ForeignKeyConstraint
from sqlalchemy import String, Integer, Float, DateTime
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import mapped_column, relationship, Mapped, DeclarativeBase
from sqlalchemy.types import LargeBinary
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime

PROBE_SENSOR_NAMES = ["p1", "p2", "p3"]

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
    info: Mapped[str] = mapped_column(String(), nullable=True, unique=False)
    calibration_id: Mapped[int] = mapped_column(ForeignKey("module_calibration.id"), nullable=True) # MAKE FALSE
    
    calibration: Mapped["ModuleCalibration"] = relationship(back_populates="module", single_parent=True)
    data: Mapped[List["Data"]] = relationship(back_populates="module")
    bb_resistance_path_data: Mapped[List["BbResistancePathData"]] = relationship(back_populates="module")
    all_calibrations: Mapped[List["SensorCalibration"]] = relationship(back_populates="module")
    
    def calib_map(self) -> dict:
        return {
            "E1": self.calibration.E1,
            "E2": self.calibration.E2,
            "E3": self.calibration.E3,
            "E4": self.calibration.E4,
            "L1": self.calibration.L1,
            "L2": self.calibration.L2,
            "L3": self.calibration.L3,
            "L4": self.calibration.L4,
            "P1": self.calibration.P1,
            "P2": self.calibration.P2,
            "P3": self.calibration.P3
        }

    def __repr__(self) -> str:
        return f"Module(id={self.id!r}, name={self.name!r})"

class Data(Base):
    __tablename__ = "data"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("run.id"), nullable=False, index=True)
    control_board_id: Mapped[int] = mapped_column(ForeignKey("control_board.id"), nullable=True)
    control_board_position: Mapped[int] = mapped_column(Integer, nullable=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("module.id"), index=True, nullable=False)
    module_orientation: Mapped[str] = mapped_column(String(50), nullable=True) # up or down, relative to the beam pipe
    plate_position: Mapped[int] = mapped_column(Integer, nullable=True) # 1, 2, 3, 4, etc...

    sensor: Mapped[str] = mapped_column(String(50), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    raw_adc: Mapped[str] = mapped_column(String(50))

    @hybrid_property
    def volts(self) -> float:
        if self.sensor.lower() in PROBE_SENSOR_NAMES:
            return None
        num = int(str(self.raw_adc)[:-2], 16)
        return 2.5 + (num / 2**15 - 1) * 1.024 * 2.5 / 1

    @hybrid_property
    def ohms(self) -> float:
        if self.sensor.lower() in PROBE_SENSOR_NAMES:
            return None
        return 1E3 / (5 / self.volts - 1)
    
    @hybrid_property
    def celcius(self) -> float:
        value_to_convert = self.ohms
        if self.sensor.lower() in PROBE_SENSOR_NAMES:
            int_value = int(self.raw_adc, 16)
            # Shift right by 3 bits (ignoring the 3 least significant bits)
            int_value >>= 3
            # Check if the 12th bit is set for sign and 2's complement adjustment
            if int_value & 0x1000:
                int_value -= 0x2000
            value_to_convert = int_value * 0.0625
        
        calib_map = self.module.calib_map()
        calib_sensor = calib_map[self.sensor]
        if calib_sensor is not None:
            slope = calib_sensor.slope
            intercept = calib_sensor.intercept
            return (value_to_convert - intercept) / slope # make sure slope and intercept have units to match this equaiton!
    
    module: Mapped["Module"] = relationship(back_populates="data")
    run: Mapped["Run"] = relationship(back_populates="data")
    control_board: Mapped["ControlBoard"] = relationship(back_populates="data")

    def __repr__(self) -> str:
        return f"Data(id={self.id!r}, module_id={self.module_id!r}, sensor={self.sensor!r}, timestamp={self.timestamp!r}, raw_adc={self.raw_adc!r}, voltage={self.volts!r}, resistance={self.ohms!r}, temperature={self.celcius!r})"

class BbResistancePathData(Base):
    __tablename__ = "bb_resistance_path_data"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("run.id"), nullable=False, index=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("module.id"), index=True, nullable=False)
    module_orientation: Mapped[str] = mapped_column(String(50), nullable=True) # up or down, relative to the beam pipe
    plate_position: Mapped[int] = mapped_column(Integer, nullable=True) # 1, 2, 3, 4, etc...

    ref_resistor_value: Mapped[float] = mapped_column(Float, nullable=False)
    path_id: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    raw_voltage: Mapped[float] = mapped_column(Float)

    run: Mapped["Run"] = relationship(back_populates="bb_resistance_path_data")
    module: Mapped["Module"] = relationship(back_populates="bb_resistance_path_data")

    @hybrid_property
    def ohms(self) -> float:
        if self.raw_voltage == 3.3:
            return 0
        return self.raw_voltage * self.ref_resistor_value / (3.3 - self.raw_voltage)

class Run(Base):
    __tablename__ = "run"
    id: Mapped[int] = mapped_column(primary_key=True)
    mode: Mapped[str] = mapped_column(String(50), nullable=False, unique=False)
    comment: Mapped[str] =  mapped_column(String(500), nullable=True, unique=False)
    cold_plate_id: Mapped[int] = mapped_column(ForeignKey("cold_plate.id"), nullable=True)
    
    cold_plate: Mapped["ColdPlate"] = relationship(back_populates="run")
    data: Mapped[List["Data"]] = relationship(back_populates="run")
    bb_resistance_path_data: Mapped[List["BbResistancePathData"]] = relationship(back_populates="run")

    notes: Mapped[List["RunNote"]] = relationship(back_populates="run")

    def __repr__(self) -> str:
        return f"Run(id={self.id!r}, mode={self.mode!r}), comment={self.comment!r}"
    

class RunNote(Base):
    __tablename__ = "run_note"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("run.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str] = mapped_column(String, nullable=False)

    run: Mapped["Run"] = relationship(back_populates="notes")


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
    slope: Mapped[float] = mapped_column(Float, nullable=False) # SHOULD BE READING/REF for example: OHMS/CELCIUS or PROBE_TEMP/REF_TEMP
    intercept: Mapped[float] = mapped_column(Float, nullable=False) # Reading offset for example Ohms

    celcius: Mapped[ARRAY[float]] = mapped_column(ARRAY(Float), nullable=True)
    ohms: Mapped[ARRAY[float]] = mapped_column(ARRAY(Float), nullable=True)
    raw_adc: Mapped[ARRAY[str]] = mapped_column(ARRAY(String(50)), nullable=True)
    times: Mapped[ARRAY[DateTime]] = mapped_column(ARRAY(DateTime), nullable=True)
    all_raw_adcs: Mapped[ARRAY[str]] = mapped_column(ARRAY(String(50)), nullable=True)
    all_raw_times: Mapped[ARRAY[DateTime]] = mapped_column(ARRAY(DateTime), nullable=True)

    module: Mapped["Module"] = relationship(back_populates="all_calibrations")

    def __repr__(self) -> str:
        return f"SensorCalibration(id={self.id!r}, module_id={self.module_id!r}, sensor={self.sensor!r}, slope={self.slope!r}, intercept={self.intercept!r})"

class ModuleCalibration(Base):
    __tablename__ = "module_calibration"
    id: Mapped[int] = mapped_column(primary_key=True)
    comment: Mapped[str] = mapped_column(String(500), nullable=True)

    E1_id: Mapped[int] = mapped_column(ForeignKey("sensor_calibration.id", use_alter=True), nullable=True)
    E2_id: Mapped[int] = mapped_column(ForeignKey("sensor_calibration.id", use_alter=True), nullable=True)
    E3_id: Mapped[int] = mapped_column(ForeignKey("sensor_calibration.id", use_alter=True), nullable=True)
    E4_id: Mapped[int] = mapped_column(ForeignKey("sensor_calibration.id", use_alter=True), nullable=True)

    L1_id: Mapped[int] = mapped_column(ForeignKey("sensor_calibration.id", use_alter=True), nullable=True)
    L2_id: Mapped[int] = mapped_column(ForeignKey("sensor_calibration.id", use_alter=True), nullable=True)
    L3_id: Mapped[int] = mapped_column(ForeignKey("sensor_calibration.id", use_alter=True), nullable=True)
    L4_id: Mapped[int] = mapped_column(ForeignKey("sensor_calibration.id", use_alter=True), nullable=True)

    P1_id: Mapped[int] = mapped_column(ForeignKey("sensor_calibration.id", use_alter=True), nullable=True)
    P2_id: Mapped[int] = mapped_column(ForeignKey("sensor_calibration.id", use_alter=True), nullable=True)
    P3_id: Mapped[int] = mapped_column(ForeignKey("sensor_calibration.id", use_alter=True), nullable=True)

    E1: Mapped["SensorCalibration"] = relationship("SensorCalibration", foreign_keys=[E1_id], post_update=True)
    E2: Mapped["SensorCalibration"] = relationship("SensorCalibration", foreign_keys=[E2_id], post_update=True)
    E3: Mapped["SensorCalibration"] = relationship("SensorCalibration", foreign_keys=[E3_id], post_update=True)
    E4: Mapped["SensorCalibration"] = relationship("SensorCalibration", foreign_keys=[E4_id], post_update=True)
    L1: Mapped["SensorCalibration"] = relationship("SensorCalibration", foreign_keys=[L1_id], post_update=True)
    L2: Mapped["SensorCalibration"] = relationship("SensorCalibration", foreign_keys=[L2_id], post_update=True)
    L3: Mapped["SensorCalibration"] = relationship("SensorCalibration", foreign_keys=[L3_id], post_update=True)
    L4: Mapped["SensorCalibration"] = relationship("SensorCalibration", foreign_keys=[L4_id], post_update=True)

    P1: Mapped["SensorCalibration"] = relationship("SensorCalibration", foreign_keys=[P1_id], post_update=True)
    P2: Mapped["SensorCalibration"] = relationship("SensorCalibration", foreign_keys=[P2_id], post_update=True)
    P3: Mapped["SensorCalibration"] = relationship("SensorCalibration", foreign_keys=[P3_id], post_update=True)

    module: Mapped["Module"] = relationship(back_populates="calibration")   

    def __repr__(self) -> str:
        return f"ModuleCalibration(id={self.id!r}, comment={self.comment!r})"