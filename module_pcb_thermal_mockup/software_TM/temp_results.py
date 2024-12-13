import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator

# Equations for temperature based on channel (MO)
channel_equations = {
    1: lambda ohms: (ohms - 770.5940437534044) / 2.45243888566309,
    3: lambda ohms: (ohms - 721.7439900388565) / 2.3023128110621,
    5: lambda ohms: (ohms - 699.5220026814853) / 2.225167884389884,
    8: lambda ohms: (ohms - 720.5058126217674) / 2.2841670806640177,
}

# Read the CSV file
df = pd.read_csv('calibration-data-2024-05-28_10-10-38.csv')

# Convert the 'Timestamp' column to datetime
df['Timestamp'] = pd.to_datetime(df['Timestamp'])

# Calculate the temperature for each channel
df['Temperature'] = df.apply(lambda row: channel_equations[row['Channel']](row['Ohms']), axis=1)

colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k']
plt.figure(figsize=(14, 8))



# --------------------------------------------------------
# Uncomment to create individual plots for each channel
# --------------------------------------------------------
for idx, channel in enumerate(df['Channel'].unique()):
    f = plt.figure(idx)
    plt.figure(figsize=(14, 8))
    channel_data = df[df['Channel'] == channel]
    plt.scatter(channel_data['Timestamp'], channel_data['Temperature'], label=f'Channel {channel}', color=colors[idx % len(colors)])
    plt.xlabel('Timestamp')
    plt.ylabel('Temperature (°C)')
    plt.title(f'Temperature vs Time for Channel {channel}')
    plt.legend()
    ax = plt.gca()
    ax.xaxis.set_major_locator(MaxNLocator(nbins=10))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M:%S'))
    plt.xticks(rotation=10)
    plt.tight_layout()
    
plt.show()


'''
# Create a single plot with all channels
for idx, channel in enumerate(df['Channel'].unique()):
    channel_data = df[df['Channel'] == channel]
    plt.scatter(channel_data['Timestamp'], channel_data['Temperature'], label=f'Channel {channel}', color=colors[idx % len(colors)])

plt.xlabel('Timestamp')
plt.ylabel('Temperature (°C)')
plt.title('Temperature vs Time for All ETROC Channels')
plt.legend()

ax = plt.gca()
ax.xaxis.set_major_locator(MaxNLocator(nbins=10)) 
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M:%S'))
plt.xticks(rotation=10)

plt.tight_layout()
plt.show()
'''

# Calculate min, max, average temperature and temperature differences for each channel
analysis_results = {}
for channel in df['Channel'].unique():
    channel_data = df[df['Channel'] == channel]
    min_temp = channel_data['Temperature'].min()
    max_temp = channel_data['Temperature'].max()
    avg_temp = channel_data['Temperature'].mean()
    temp_diff = max_temp - min_temp
    analysis_results[channel] = {
        'Min Temperature': min_temp,
        'Max Temperature': max_temp,
        'Average Temperature': avg_temp,
        'Temperature Difference': temp_diff
    }

# Print analysis results
for channel, results in analysis_results.items():
    print(f"Channel {channel}:")
    print(f"  Min Temperature: {results['Min Temperature']:.2f} °C")
    print(f"  Max Temperature: {results['Max Temperature']:.2f} °C")
    print(f"  Average Temperature: {results['Average Temperature']:.2f} °C")
    print(f"  Temperature Difference: {results['Temperature Difference']:.2f} °C")
    print()

# Save analysis results to a CSV file
analysis_df = pd.DataFrame.from_dict(analysis_results, orient='index')
analysis_df.index.name = 'Channel'
analysis_df.to_csv('temperature_analysis_results.csv')