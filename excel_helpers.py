import pandas as pd
import json

# Read the Excel file into a DataFrame
df = pd.read_excel('files/input/eksperdid.xlsx')

# Create an empty list to store dictionaries
json_list = []

# Get column names for generating the description
column_names = df.columns[5:93].tolist()

# Loop through each row in the DataFrame
for index, row in df.iterrows():
    entry = {}

    # Generate 'name' value
    if pd.notna(row['Eksperdi eesnimi']) or pd.notna(row['Middle_Name']) or pd.notna(row['Eksperdi perekonnanimi']):
        entry['name'] = ' '.join(
            filter(pd.notna, [row['Eksperdi eesnimi'], row['Middle_Name'], row['Eksperdi perekonnanimi']]))
    else:
        entry['name'] = row['Terminikomisjon/\ntöörühm/erialaliit vm']

    # Generate 'description' value
    description_values = []
    for col_name, val in zip(column_names, row.iloc[5:93]):
        if col_name == 'Notes\n Märkmed':  # Replace this with the actual name of column 'N' if different
            continue  # Skip this column
        if pd.notna(val):
            formatted_col_name = col_name.replace("\n", " / ")
            description_values.append(f"{formatted_col_name}: {str(val)}")

    if description_values:
        entry['description'] = '. '.join(description_values) + '.'

    # Append the dictionary to the list
    json_list.append(entry)

# Write the list of dictionaries to a JSON file
with open('files/input/eksperdid.json', 'w', encoding='utf-8') as f:
    json.dump(json_list, f, ensure_ascii=False, indent=4)
