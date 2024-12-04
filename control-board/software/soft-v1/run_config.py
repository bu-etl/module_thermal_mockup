from pydantic import BaseModel, PositiveInt, Field, field_validator, model_validator
from typing import Literal, Optional, Any, Self

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