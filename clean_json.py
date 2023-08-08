import json
import re

def apply_regex(value, regex_patterns_and_replacements):
    """
    If value is a string, apply the regex patterns and replacements.
    If value is a dictionary or list, recursively process its elements.
    """
    if isinstance(value, str):
        for pattern, replacement in regex_patterns_and_replacements:
            value = re.sub(pattern, replacement, value)
    elif isinstance(value, dict):
        value = {k: apply_regex(v, regex_patterns_and_replacements) for k, v in value.items()}
    elif isinstance(value, list):
        value = [apply_regex(v, regex_patterns_and_replacements) for v in value]
    return value

def clean_json_file(file_name, regex_patterns_and_replacements):
    # Load data from the JSON file
    with open(file_name, 'r') as f:
        data = json.load(f)

    # Recursively apply regex patterns and replacements to the data
    cleaned_data = apply_regex(data, regex_patterns_and_replacements)

    # Write the cleaned data back to the JSON file
    with open(file_name, 'w') as f:
        json.dump(cleaned_data, f, indent=4)

# List of regex patterns and replacements
# Replace this with your actual patterns and replacements
regex_patterns_and_replacements = [
    (r'pattern1', 'replacement1'),
    (r'pattern2', 'replacement2'),
    # Add more as needed...
]

# File name
file_name = 'concepts.json'

# Call the function
clean_json_file(file_name, regex_patterns_and_replacements)
