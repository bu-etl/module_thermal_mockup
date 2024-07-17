import pandas as pd

def find_closest_rows_per_channel(input_file, dates_to_search, temps_to_append, output_file, n=5):
   
    df = pd.read_csv(input_file)
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    dates_to_search = pd.to_datetime(dates_to_search)

    closest_rows = pd.DataFrame()
    grouped = df.groupby('Channel')
    
    for date, temp in zip(dates_to_search, temps_to_append):
        for channel, group in grouped:
           
            group['time_diff'] = (group['Timestamp'] - date).abs()
            closest_n_rows = group.nsmallest(n, 'time_diff')
            closest_n_rows['Temperature'] = temp
            closest_rows = pd.concat([closest_rows, closest_n_rows], ignore_index=True)
    
    closest_rows = closest_rows.drop(columns=['time_diff'])
    closest_rows.to_csv(output_file, index=False)
    
    print(f"Filtered data saved to {output_file}")

# Define the array of specific dates and times
dates_to_search = [
    '2024-07-12T14:59:45',
    '2024-07-12T15:22:05',
    '2024-07-12T15:57:35',
    '2024-07-12T16:12:44',
    '2024-07-12T16:36:56',
    '2024-07-12T16:54:43'
]

# Define the corresponding temperatures
temps_to_append = [
    -33.1,  # Temperature for '2024-07-12T14:59:45'
    -28.5,  # Temperature for '2024-07-12T15:22:05'
    -23.5,  # Temperature for '2024-07-12T14:57:35'
    -18.5,  # Temperature for '2024-07-12T16:12:44'
    -13.5,  # Temperature for '2024-07-12T16:36:56'
    -8.5,   # Temperature for '2024-07-12T16:54:43'
]

input_file = 'parsed_calibration-data-2024-07-12_14-49-05.csv'
output_file = 'time_calibration-data-2024-07-12_14-49-05.csv'
find_closest_rows_per_channel(input_file, dates_to_search, temps_to_append, output_file)
