from typing import List
from typing import Optional
from sqlalchemy import ForeignKey
from sqlalchemy import String, Integer, Float, DateTime
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
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
    modules: Mapped[List["Module"]] = relationship(back_populates="control_board")

    def __repr__(self) -> str:
        return f"ControlBoard(id={self.id!r}, name={self.name!r})"

class Module(Base):
    __tablename__ = "module"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    position_on_D: Mapped[str] = mapped_column(String(50), nullable=True, unique=True)
    control_board_id: Mapped[int] = mapped_column(ForeignKey("control_board.id"), nullable=True)
    control_board_pos: Mapped[str] = mapped_column(String(1), nullable=True)

    control_board: Mapped["ControlBoard"] = relationship(back_populates="modules")
    data: Mapped[List["Data"]] = relationship(back_populates="module")

    def __repr__(self) -> str:
        return f"Module(id={self.id!r}, name={self.name!r}, position_on_D={self.position_on_D!r}, control_board_pos={self.control_board_pos!r})"

class Data(Base):
    __tablename__ = "data"
    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("module.id"))
    sensor: Mapped[str] = mapped_column(String(50))
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    raw_adc: Mapped[str] = mapped_column(String(50))
    volts: Mapped[float] = mapped_column(Float)
    ohms: Mapped[float] = mapped_column(Float) 
    celcius: Mapped[float] = mapped_column(Float) 

    run_id: Mapped[int] = mapped_column(ForeignKey("run.id"), nullable=False)

    module: Mapped["Module"] = relationship(back_populates="data")
    run: Mapped["Run"] = relationship(back_populates="data")

    def __repr__(self) -> str:
        return f"Data(id={self.id!r}, module_id={self.module_id!r}, sensor={self.sensor!r}, timestamp={self.timestamp!r}, raw_adc={self.raw_adc!r}, voltage={self.volts!r}, resistance={self.ohms!r}, temperature={self.celcius!r})"
    
class Run(Base):
    __tablename__ = "run"
    id: Mapped[int] = mapped_column(primary_key=True)
    mode: Mapped[str] = mapped_column(String(50), nullable=False, unique=False)
    comment: Mapped[str] =  mapped_column(String(500), nullable=True, unique=False)

    data: Mapped[List["Data"]] = relationship(back_populates="run")

    def __repr__(self) -> str:
        return f"Run(id={self.id!r}, mode={self.mode!r}), comment={self.comment!r}"