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
# volts = codes * 1.024 * (3.3/2) / 2.56
volts = 1.65 + (codes/2**23 - 1) * 1.024 * 1.65 / 1
print(volts)

# V = 3.3 * (R / (R+47.5E3))
ohms = 0.25 * 47.5E3 / (3.3 / volts - 1)
print(ohms)

plt.plot([0, -5, -10, -15], ohms[0, :], marker='.', label='Channel 1')
plt.plot([0, -5, -10, -15], ohms[1, :], marker='.', label='Channel 3')
plt.plot([0, -5, -10, -15], ohms[2, :], marker='.', label='Channel 5')
plt.plot([0, -5, -10, -15], ohms[3, :], marker='.', label='Channel 8')
plt.ylabel('Ohms per Sensor')
plt.xlabel('Temp C')
plt.legend()
plt.tight_layout()
plt.show()
