import json

# Open the JSON file for reading
with open('failid/andmestik/keelevaraga/ekilex_import_data_inter.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Check if the data is a list and print its length
if isinstance(data, list):
    print("Count of objects:", len(data))
# Check if the data is a dictionary and print its length
elif isinstance(data, dict):
    print("Count of objects:", len(data.keys()))
else:
    print("The JSON file does not contain a list or dictionary.")
