import pandas as pd
import json


input_excel = 'files/input/eksperdid.xlsx'
output_json = 'files/output/eksperdid.json'


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
            if col_name == 'Notes\n Märkmed':  # Replace this with the actual name of column 'N' if different
                continue  # Skip this column
            if pd.notna(val):
                formatted_col_name = col_name.replace("\n", " / ")
                description_values.append(f"{formatted_col_name}: {str(val)}")

        if description_values:
            entry['description'] = '. '.join(description_values) + '.'

        json_list.append(entry)

    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(json_list, f, ensure_ascii=False, indent=4)


def create_experts_sources(input_excel, input_json, output_json):
    # Merge Excel info to experts info extracted from Esterm
    return output_json