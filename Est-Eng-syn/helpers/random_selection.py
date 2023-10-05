import json
import random

# Load the JSON file
with open('output/cleaned_data_itermax.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Check if the data length is greater than 1000
if len(data) >= 1000:
    # Select 100 random objects
    random_selection = random.sample(data, 1000)
else:
    print("The JSON file contains less than 100 objects.")

# Save the random selection to a new JSON file
with open('random_1000_cleaned.json', 'w', encoding='utf-8') as f:
    json.dump(random_selection, f, ensure_ascii=False, indent=4)
