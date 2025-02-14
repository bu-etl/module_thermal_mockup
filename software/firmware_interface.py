"""
These classes tell you how to read sensor data from a module
based on different firmware versions
"""
from abc import ABC, abstractmethod
class ModuleFirmwareInterface(ABC):
    """Abstract base class to enforce the read and write methods of inherited classes"""
    
    @abstractmethod
    def read_sensor(self, adc_value: str) -> str:
        """Read adc output string"""
        ...

    @abstractmethod
    def write_sensor(self, sensor_name: str) -> str:
        """Write ADC command"""
        ...

    @abstractmethod
    def write_sensors(self, sensor_names: list[str]) -> str:
        """measures all sensors on module"""
        ...

    @abstractmethod
    def data_line_length(self, sensor_name: str) -> int:
        """line length of from the serial monitor so for example: "measure 1 72a4ff" or "Probe 1: 0xb53" """
        ...


class ControlBoardV1(ModuleFirmwareInterface):
    __firmware_name__ = "Control Board V1"
    def __init__(self, control_board_pos: int):
        self.control_board_pos = control_board_pos
        self.sensor_map = {
            'E3': 1,
            'L1': 2,
            'E1': 3,
            'L2': 4,
            'E2': 5,
            'L3': 6,
            'L4': 7,
            'E4': 8
        }
        """
        TM -ab, TM -abcd, TM measure 1
        """
    def read_sensor(self, adc_value: str) -> str:
        """An example is "TM -a measure 1 72a4ff" """
        return adc_value.split()[-1]

    def write_sensor(self, sensor_name: str) -> str:
        """An example is "TM -a measure 1" """
        return f"TM -{self.control_board_pos} measure {self.sensor_map[sensor_name]}"

    def write_sensors(self, sensor_names: list[str]) -> str:
        channels = [str(self.sensor_map[sensor_name]) for sensor_name in sensor_names]
        return f"TM -{self.control_board_pos} measure {' '.join(channels)}"
    
    def data_line_length(self, sensor_name: str) -> int:
        if 'p' in sensor_name.lower():
            raise NotImplementedError("probe not implemented")
        elif 'e' in sensor_name.lower() or 'l' in sensor_name.lower():
            return 22
        else:
            raise NotImplementedError(f'unknown sensor name: {sensor_name}') 
           
class ThermalMockupV2(ModuleFirmwareInterface):
    __firmware_name__ = "Thermal Mockup V2"

    def __init__(self):
        self.sensor_map = {
            'E3': 1,
            'L1': 2,
            'E1': 3,
            'L2': 4,
            'E2': 5,
            'L3': 6,
            'L4': 7,
            'E4': 8,
            'P1': 1,
            'P2': 2,
            'P3': 3
        }

    def read_sensor(self, adc_value: str) -> str:
        """An example is "measure 1 72a4ff" """
        return adc_value.split()[-1] #should still work for probes

    def write_sensor(self, sensor_name: str) -> str:
        #would need to map sensor name to channel
        if 'p' in sensor_name.lower():
            return f'probe {self.sensor_map[sensor_name]}'
        elif 'e' in sensor_name.lower() or 'l' in sensor_name.lower():
            return f"measure {self.sensor_map[sensor_name]}"
        else:
            raise NotImplementedError(f'unknown sensor name: {sensor_name}')         

    def write_sensors(self, sensor_names: list[str]) -> str:
        etroc_lgad_channels = [str(self.sensor_map[sensor_name]) for sensor_name in sensor_names if 'p' not in sensor_name.lower()]
        probe_channels = [str(self.sensor_map[sensor_name]) for sensor_name in sensor_names if 'p' in sensor_name.lower()]

        etroc_lgad_command = f"measure {' '.join(etroc_lgad_channels)}" if etroc_lgad_channels else ''
        probe_command = f"probe {' '.join(probe_channels)}" if probe_channels else ''  
        return f"{etroc_lgad_command} \n {probe_command}"  

    def data_line_length(self, sensor_name:str) -> int:
        if 'p' in sensor_name.lower():
            return 14
        elif 'e' in sensor_name.lower() or 'l' in sensor_name.lower():
            return 16
        else:
            raise NotImplementedError(f'unknown sensor name: {sensor_name}') 
           

def available_firmwares():
    return [subclass.__firmware_name__ for subclass in ModuleFirmwareInterface.__subclasses__()]

def firmware_select(firmware_name: str) -> ModuleFirmwareInterface:
    for subclass in ModuleFirmwareInterface.__subclasses__():
        if subclass.__firmware_name__ == firmware_name:
            return subclass()