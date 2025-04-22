"""
These classes tell you how to read sensor data from a module
based on different firmware versions
"""
from abc import ABC, abstractmethod
import re
from typing import Any

class ModuleFirmwareInterface(ABC):
    """Abstract base class to enforce the read and write methods of inherited classes"""
    
    @abstractmethod
    def read_sensor(self, raw_output: str) -> str:
        """Read string from arduino"""
        ...

    @abstractmethod
    def read_probe(self, raw_output: str) -> str:
        """Read string from arduino"""
        ...

    @abstractmethod
    def write_sensors(self, sensor_names: list[str]) -> str:
        """measures all sensors on module"""
        ...

    @abstractmethod
    def write_probes(self, probe_names: list[str]) -> str:
        """measures all pcb temperature probes on module"""
        ...

    @abstractmethod
    def write_bbs(self, tp_n: list[int]):
        """Command to read the bump bond values"""
        ...
    
    @abstractmethod
    def read_bb(self, raw_output: str) -> tuple[Any, Any]:
        """Should return the bb path id and then the output"""
        ...

# class ControlBoardV1(ModuleFirmwareInterface):
#     __firmware_name__ = "Control Board V1"
#     def __init__(self, control_board_pos: int):
#         self.control_board_pos = control_board_pos
#         self.sensor_map = {
#             'E3': 1,
#             'L1': 2,
#             'E1': 3,
#             'L2': 4,
#             'E2': 5,
#             'L3': 6,
#             'L4': 7,
#             'E4': 8
#         }
#         """
#         TM -ab, TM -abcd, TM measure 1
#         """
#     def read_sensor(self, adc_value: str) -> str:
#         """An example is "TM -a measure 1 72a4ff" """
#         return adc_value.split()[-1]

#     def write_sensors(self, sensor_names: list[str]) -> str:
#         channels = [str(self.sensor_map[sensor_name]) for sensor_name in sensor_names]
#         return f"TM -{self.control_board_pos} measure {' '.join(channels)}"
    
#     def write_bb(self, tp_n: list[int]) -> str:
#         raise NotImplementedError("Needs to be implementented")
    
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
        }

        self.swapped_sensor_map = dict(
            zip(self.sensor_map.values(), self.sensor_map.keys()))

        self.probe_map = {
            'P1': 1,
            'P2': 2,
            'P3': 3 
        }

        self.swapped_probe_map = dict(
            zip(self.probe_map.values(), self.probe_map.keys()))

    def read_sensor(self, raw_output: str) -> tuple[int, str]:
        pattern = re.compile(r"^measure (\d+) (\S+)$")
        match = re.match(pattern, raw_output)
        if match:
            channel, adc_value = match.groups()
            sensor = self.swapped_sensor_map[int(channel)]
            return sensor, adc_value 

    def write_sensors(self, sensors: list[str]):
        if not isinstance(sensors, list):
            raise TypeError("Sensors needs to be a list of sensors you want to read")
        if len(sensors) == 0:
            raise ValueError("List length cannot be 0")
        
        sensor_ids = []
        for sensor in sensors:
            if sensor not in self.sensor_map:
                raise ValueError(f"Sensor {sensor} is not a valid sensor name")
            sensor_ids.append(self.sensor_map[sensor])
        return f'measure ' + ' '.join(map(str,sensor_ids))

    def read_probe(self, raw_output: str) -> tuple[int, str]:
        pattern = re.compile(r"^Probe (\d+): (\S+)$")
        match = re.match(pattern, raw_output)
        if match:
            probe_id, adc_value = match.groups()
            probe = self.swapped_probe_map[int(probe_id)]
            return probe, adc_value   

    def write_probes(self, probes: list[str]) -> str:
        if not isinstance(probes, list):
            raise TypeError("Probes needs to be a list of probes you want to read")
        if len(probes) == 0:
            raise ValueError("List length cannot be 0")
        
        probe_ids = []
        for probe in probes:
            if probe not in self.probe_map:
                raise ValueError(f"Probe {probe} is not a valid probe name")
            probe_ids.append(self.probe_map[probe])
        return f'probe ' + ' '.join(map(str,probe_ids))
        
    def write_bbs(self, tp_n: list[int]) -> str:
        """
        If the arduino has the automatic bump bond readout through the analog pins as defined:
        https://bu.nebraskadetectorlab.com/submission/shared/3724/ZRg7YayBwd3sNfJXLnzcIFojWbO2De

        This command yields the string to send that command.
        """
        if not isinstance(tp_n, list):
            raise TypeError("Input is not a list type")
        if len(tp_n) == 0:
            raise ValueError("List length cannot be 0")
        
        return f"TP " + ' '.join(map(str,tp_n))
                
    def read_bb(self, raw_output: str) -> tuple[int, float]:
        """Returns the bump bond path id and the corresponding value if string matches"""
        if not isinstance(raw_output, str):
            return
        pattern = re.compile(r"^TP(\d+) (\S+)$")
        match = re.match(pattern, raw_output)
        if match:
            bb_path_id, raw_value = match.groups()
            return int(bb_path_id), float(raw_value)
           
def available_firmwares():
    return [subclass.__firmware_name__ for subclass in ModuleFirmwareInterface.__subclasses__()]

def firmware_select(firmware_name: str) -> ModuleFirmwareInterface:
    for subclass in ModuleFirmwareInterface.__subclasses__():
        if subclass.__firmware_name__ == firmware_name:
            return subclass()