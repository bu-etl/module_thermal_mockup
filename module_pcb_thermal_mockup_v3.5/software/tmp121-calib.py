import matplotlib.pyplot as plt
import pandas as pd

def hex_to_temperature(hex_value):
    # Ensure the value is interpreted as a hexadecimal string
    int_value = int(hex_value, 16)
    
    # Shift right by 3 bits (ignoring the 3 least significant bits)
    int_value >>= 3
    
    # Check if the 12th bit is set for sign and 2's complement adjustment
    if int_value & 0x1000:
        int_value -= 0x2000
    
    temperature = int_value * 0.0625
    return temperature

values = [
    ['0xf2d1', '0xf539', '0xf7b9', '0xfa29', '0xfc19'],
    ['0xf289', '0xf4f9', '0xf779', '0xf9e9', '0xfbe1'],
    ['0xf291', '0xf501', '0xf779', '0xf9e9', '0xfbe1'],
]

print("Raw ADC Values (Hex):")
for row in values:
    print(row)

# Convert hex values to temperatures
temperatures_converted = [[hex_to_temperature(hex_val) for hex_val in row] for row in values]

temperatures_df = pd.DataFrame(temperatures_converted)
print("\nTemperatures:")
print(temperatures_df)

reference_temperatures = [-28.5, -23.5, -18.5, -13.5, -8.5]

# Subtract the respective reference temperatures from each column
for i, ref_temp in enumerate(reference_temperatures):
    temperatures_df[i] = temperatures_df[i] - ref_temp

print("\nTemperature differences:")
print(temperatures_df)
