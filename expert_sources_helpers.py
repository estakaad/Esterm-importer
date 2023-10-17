import pandas as pd
import json


input_excel = 'files/input/eksperdid.xlsx'
output_json = 'files/input/eksperdid.json'
expert_info_from_esterm = 'files/input/eksperdid_estermist.csv'
expert_info_for_api_calls = 'files/output/expert_sources.json'

def excel_to_json(input_filename, output_filename):
    df = pd.read_excel(input_filename)

    json_list = []

    column_names = df.columns[5:93].tolist()

    for index, row in df.iterrows():
        entry = {}

        if pd.notna(row['Eksperdi eesnimi']) or pd.notna(row['Middle_Name']) or pd.notna(row['Eksperdi perekonnanimi']):
            entry['name'] = ' '.join(
                filter(pd.notna, [row['Eksperdi eesnimi'], row['Middle_Name'], row['Eksperdi perekonnanimi']]))
        else:
            entry['name'] = row['Terminikomisjon/\ntöörühm/erialaliit vm']

        description_values = []
        for col_name, val in zip(column_names, row.iloc[5:93]):
            if col_name == 'Notes\nMärkmed':
                continue
            if pd.notna(val):
                formatted_col_name = col_name.replace("\n", " / ")
                description_values.append(f"{formatted_col_name}: {str(val)}")

        if description_values:
            entry['description'] = '. '.join(description_values) + '.'

        json_list.append(entry)

    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(json_list, f, ensure_ascii=False, indent=4)


def create_experts_sources(output_json, expert_info_from_esterm, expert_info_for_api_calls):
    import json
    import csv

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
            api_dict["description"] += ", " + json_dict[name]
        api_list.append(api_dict)

    with open(expert_info_for_api_calls, "w", encoding='utf-8') as api_file:
        json.dump(api_list, api_file, indent=4, ensure_ascii=False)

#excel_to_json(input_excel, output_json)
#create_experts_sources(output_json, expert_info_from_esterm, expert_info_for_api_calls)