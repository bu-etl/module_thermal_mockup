import numpy as np
import matplotlib.pyplot as plt

codes = np.array([
    [0.027315, 0.027057, 0.026816, 0.026581],
    [0.026340, 0.026100, 0.025872, 0.025650],
    [0.025895, 0.025666, 0.025444, 0.025228],
    [0.026315, 0.026074, 0.025858, 0.025627],
])

print(codes)

codes = (2**24-1)*codes
print("\nRaw ADC Values (Hex):")
for row in codes:
    print([hex(int(value)) for value in row])
print()

# volts = codes * 1.024 * (3.3/2) / 2.56
volts = 1.65 + (codes/2**23 - 1) * 1.024 * 1.65 / 1
print(volts)
print()

# V = 3.3 * (R / (R+47.5E3))
ohms3 = 47.5E3 / (3.3 / volts - 1)
print(ohms3)
print()

ohms4 = 0.25 * 47.5E3 / (3.3 / volts - 1)
print(ohms4)
print()

temp = np.array([0, -5, -10, -15])

# find linear fit based on each channel for ohms3
a1_3, b1_3 = np.polyfit(temp, ohms3[0, :], 1)
a3_3, b3_3 = np.polyfit(temp, ohms3[1, :], 1)
a5_3, b5_3 = np.polyfit(temp, ohms3[2, :], 1)
a8_3, b8_3 = np.polyfit(temp, ohms3[3, :], 1)

print("Equation 3:")
print(f"Channel 1 (ohms3): {a1_3}*Temp + {b1_3} = Ohms")
print(f"Channel 3 (ohms3): {a3_3}*Temp + {b3_3} = Ohms")
print(f"Channel 5 (ohms3): {a5_3}*Temp + {b5_3} = Ohms")
print(f"Channel 8 (ohms3): {a8_3}*Temp + {b8_3} = Ohms")

# Plot for ohms3
eq3 = plt.figure(1)
plt.scatter(temp, ohms3[0, :], label='Channel 1 Data')
plt.scatter(temp, ohms3[1, :], label='Channel 3 Data')
plt.scatter(temp, ohms3[2, :], label='Channel 5 Data')
plt.scatter(temp, ohms3[3, :], label='Channel 8 Data')

plt.plot(temp, a1_3*temp+b1_3, label='Channel 1 Fit')
plt.plot(temp, a3_3*temp+b3_3, label='Channel 3 Fit')
plt.plot(temp, a5_3*temp+b5_3, label='Channel 5 Fit')
plt.plot(temp, a8_3*temp+b8_3, label='Channel 8 Fit')

plt.ylabel('Ohms per Sensor (3)')
plt.xlabel('Temp C')
plt.legend()
plt.title("Equation 3")


# find linear fit based on each channel for ohms4
a1_4, b1_4 = np.polyfit(temp, ohms4[0, :], 1)
a3_4, b3_4 = np.polyfit(temp, ohms4[1, :], 1)
a5_4, b5_4 = np.polyfit(temp, ohms4[2, :], 1)
a8_4, b8_4 = np.polyfit(temp, ohms4[3, :], 1)

print("Equation 4:")
print(f"Channel 1 (ohms4): {a1_4}*Temp + {b1_4} = Ohms")
print(f"Channel 3 (ohms4): {a3_4}*Temp + {b3_4} = Ohms")
print(f"Channel 5 (ohms4): {a5_4}*Temp + {b5_4} = Ohms")
print(f"Channel 8 (ohms4): {a8_4}*Temp + {b8_4} = Ohms")

# Plot for ohms4
eq4 = plt.figure()
plt.scatter(temp, ohms4[0, :], label='Channel 1 Data')
plt.scatter(temp, ohms4[1, :], label='Channel 3 Data')
plt.scatter(temp, ohms4[2, :], label='Channel 5 Data')
plt.scatter(temp, ohms4[3, :], label='Channel 8 Data')

plt.plot(temp, a1_4*temp+b1_4, label='Channel 1 Fit')
plt.plot(temp, a3_4*temp+b3_4, label='Channel 3 Fit')
plt.plot(temp, a5_4*temp+b5_4, label='Channel 5 Fit')
plt.plot(temp, a8_4*temp+b8_4, label='Channel 8 Fit')

plt.ylabel('Ohms per Sensor (4)')
plt.xlabel('Temp C')
plt.legend()
plt.title("Equation 4")

plt.show()