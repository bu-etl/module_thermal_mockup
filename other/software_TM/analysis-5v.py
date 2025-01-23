import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

df = pd.read_csv('time_calibration-data-2024-07-12_14-49-05.csv')
df['Timestamp'] = pd.to_datetime(df['Timestamp'])

# Convert 'ADC Value' from hexadecimal to decimal format and remove the last byte
df['ADC Value'] = df['ADC Value'].apply(lambda x: int(x[:-2], 16) if x.endswith('ff') else int(x, 16))

temperatures = [-33.1, -28.5, -23.5, -18.5, -13.5, -8.5]
average_adc_dict = {temp: [] for temp in temperatures}
channels = df['Channel'].unique()

# Calculate the average ADC value for each channel based on temperature 
for channel in channels:
    for temp in temperatures:
        avg_adc = df[(df['Channel'] == channel) & (df['Temperature'] == temp)]['ADC Value'].mean()
        average_adc_dict[temp].append(avg_adc)


average_adc_array = np.array([average_adc_dict[temp] for temp in temperatures]).T

print("Average ADC values array:")
for row in average_adc_array:
    print([hex(int(value)) for value in row])
print()

# Convert ADC values to Volts
volts = 2.5 + (average_adc_array / 2**15 - 1) * 1.024 * 2.5 / 1
print("Volts:")
print(volts)
print()

# Convert Volts to Ohms
ohms = 1E3 / (5 / volts - 1)
print("Ohms:")
print(ohms)
print()

# Calculate one-fourth of the resistance
ohms_one_fourth = 0.25 * 1E3 / (5 / volts - 1)
print("Ohms (1/4):")
print(ohms_one_fourth)
print()

# Calculate the linear fit for each channel
coefficients = {}
for i, channel in enumerate(channels):
    a, b = np.polyfit(temperatures, ohms[i, :], 1)
    coefficients[channel] = (a, b)
    print(f"Channel {channel}: {a}*Temp + {b} = Ohms")

# Plot, excluding channel 4
plt.figure(1)
for i, channel in enumerate(channels):
    if channel == 4:
        continue
    plt.scatter(temperatures, ohms[i, :], label=f'Channel {channel} Data')
    plt.plot(temperatures, coefficients[channel][0]*np.array(temperatures) + coefficients[channel][1], label=f'Channel {channel} Fit')

plt.ylabel('Ohms')
plt.xlabel('Temp (°C)')
plt.legend()
plt.title('Temperature Calibration Equations')
plt.show()
