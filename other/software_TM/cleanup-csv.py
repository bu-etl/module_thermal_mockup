
import pandas as pd

def filter_csv():
    input_file = input("Please enter the input file name (including .csv extension): ")
    output_file = "parsed_" + input_file
    
    # Load the CSV file
    df = pd.read_csv(input_file)
    columns_to_keep = ['Timestamp', 'Channel', 'ADC Value']
    df_filtered = df[columns_to_keep]
    df_filtered.to_csv(output_file, index=False)
    
    print(f"Filtered data saved to {output_file}")

filter_csv()

