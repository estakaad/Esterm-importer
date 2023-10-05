import json


def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json(data, filepath):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def extract_headword_values(data):
    return {item["headwordValue"] for item in data}


def filter_by_headword_values(data, headword_values):
    return sorted(
        [item for item in data if item["headwordValue"] in headword_values],
        key=lambda x: x["headwordValue"]
    )


def main():
    # File paths
    file1_path = "output/cleaned_data_inter.json"
    file2_path = "output/cleaned_data_itermax.json"
    output_file1_path = "output/cleaned_data_inter_compare.json"
    output_file2_path = "output/cleaned_data_itermax_compare.json"

    # Load JSON files
    data1 = load_json(file1_path)
    data2 = load_json(file2_path)

    # Extract headword values
    headword_values1 = extract_headword_values(data1)
    headword_values2 = extract_headword_values(data2)

    # Find common headword values
    common_headword_values = headword_values1.intersection(headword_values2)

    # Take first 100 (or 1000) common headword values
    selected_headword_values = set(list(common_headword_values)[:100])  # change 100 to 1000 if needed

    # Filter data based on the selected headword values
    filtered_data1 = filter_by_headword_values(data1, selected_headword_values)
    filtered_data2 = filter_by_headword_values(data2, selected_headword_values)

    # Write filtered data to new files
    write_json(filtered_data1, output_file1_path)
    write_json(filtered_data2, output_file2_path)


if __name__ == "__main__":
    main()
