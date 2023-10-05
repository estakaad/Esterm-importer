import json

# Step 1: Load the JSON file
with open('input/ekilex_import_data_itermax.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Step 2: Determine the size of each chunk
chunk_size = len(data) // 10  # Use '//' for integer division

# Step 3: Create and write to the new JSON files
for i in range(10):
    with open(f'ekilex_import_data_itermax_part_{i}.json', 'w', encoding='utf-8') as f:
        if i == 9:  # In the last file, we include the remaining entries
            chunk = data[i*chunk_size :]
        else:
            chunk = data[i*chunk_size : (i+1)*chunk_size]
        json.dump(chunk, f)
