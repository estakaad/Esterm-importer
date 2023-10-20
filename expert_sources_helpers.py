import pandas as pd
import json
import csv


def excel_to_json(input_filename, output_filename):
    df = pd.read_excel(input_filename)
    json_list = []

    column_names = df.columns[1:9].tolist()

    for index, row in df.iterrows():
        entry = {}
        description_values = []

        # Check if the names are present
        has_name = pd.notna(row['Eksperdi eesnimi']) or pd.notna(row['Eksperdi perekonnanimi'])

        # If names are present, use them. Otherwise, use the Terminikomisjon/töörühm value.
        if has_name:
            entry['name'] = ' '.join(filter(pd.notna, [row['Eksperdi eesnimi'], row['Eksperdi perekonnanimi']]))
        else:
            entry['name'] = row['Terminikomisjon/töörühm']

        # Iterate through each of the columns to build the description.
        for col_name, val in zip(column_names, row.iloc[1:9]):
            if col_name not in ["Eksperdi eesnimi", "Eksperdi perekonnanimi"]:
                if pd.notna(val) and val != entry['name']:
                    formatted_col_name = col_name.replace("\n", " / ")
                    description_values.append(f"{formatted_col_name}: {str(val)}")

        # If there are any description values, join them and add to the entry.
        if description_values:
            entry['description'] = '. '.join(description_values) + '.'

        json_list.append(entry)

    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(json_list, f, ensure_ascii=False, indent=4)


def create_experts_sources(output_json, expert_info_from_esterm, expert_info_for_api_calls):

    with open(output_json, "r", encoding='utf-8') as json_file:
        json_data = json.load(json_file)

    json_dict = {entry["name"]: entry.get("description", "") for entry in json_data if "name" in entry}

    csv_data = []
    with open(expert_info_from_esterm, "r", encoding='utf-8') as csv_file:
        csv_reader = csv.reader(csv_file)
        next(csv_reader)  # skip header
        for row in csv_reader:
            csv_data.append({"type": row[0], "name": row[1]})

    api_list = []

    for entry in csv_data:
        api_dict = {"type": "PERSON", "isPublic": False}
        name = entry["name"]
        api_dict["name"] = entry["type"]
        api_dict["description"] = name
        if name in json_dict:
            api_dict["description"] += " – " + json_dict[name]
        api_list.append(api_dict)

    with open(expert_info_for_api_calls, "w", encoding='utf-8') as api_file:
        json.dump(api_list, api_file, indent=4, ensure_ascii=False)

def create_name_and_type_to_id_mapping_for_expert_sources(expert_sources):
    name_type_to_ids = {}
    for source in expert_sources:
        source_id = source['id']
        source_name = source['name']
        source_description = source['description']

        if source_description == source_name or source_description.startswith(f"{source_name} – "):
            key = (source_name, source_description)
        else:
            key = (source_name, source_description)

        name_type_to_ids[key] = source_id

    return name_type_to_ids


def get_expert_source_id_by_name_and_type(name, type, type_desc_to_ids):
    if name == '':
        name = type.upper()
    for (source_type, source_description), source_id in type_desc_to_ids.items():
        if source_type == type and (source_description == name or source_description.startswith(f"{name} – ")):
            return source_id
    print(type + ',' + name)
    return '60181 + ' + name
