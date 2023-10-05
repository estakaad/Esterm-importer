import json
import os

# Define the folder and file names
folder_path = '../failid/andmestik/keelevaraga'
#input_file_name = 'cleaned_data_inter.json'
input_file_name = 'ekilex_import_data_inter.json'
#output_file_name = 'cleaned_data_inter_1000.json'
output_file_name = 'ekilex_import_data_inter_051023_100000.json'

# Generate full paths
input_file_path = os.path.join(folder_path, input_file_name)
output_file_path = os.path.join(folder_path, output_file_name)


count = 10000

# Read the data from input file
with open(input_file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Extract the first 10000 objects
subset_data = data[:count]

# Write the subset data to the output file
with open(output_file_path, 'w', encoding='utf-8') as f:
    json.dump(subset_data, f, indent=2, ensure_ascii=False)

print(f"First {count} objects written to {output_file_path}")
