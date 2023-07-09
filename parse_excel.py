import pandas as pd
import json
from pathlib import Path


# Import kalanduse terminikogu
dataset_code = 'kala'

script_dir = Path(__file__).resolve().parent
input_dir = script_dir / 'input'
output_dir = script_dir / 'output'

input_file = input_dir / 'kalandus.xlsx'
output_file = output_dir / 'output.json'

df = pd.read_excel(input_file, engine='openpyxl')

groups = df.groupby('E_ID')

data = []

for group_name, group_df in groups:
    definitions = group_df.drop_duplicates(subset=['L_DEF', 'L_LANG'])[['L_DEF', 'L_LANG']].to_dict('records')
    definitions = [
        {'value': d['L_DEF'], 'lang': d['L_LANG'], 'definitionTypeCode': 'definitsioon'}
        for d in definitions
        if not pd.isnull(d['L_DEF']) and not pd.isnull(d['L_LANG'])
    ]

    words = group_df.drop_duplicates(subset=['T_TERM', 'L_LANG'])[['T_TERM', 'L_LANG']].to_dict('records')
    words = [
        {'value': w['T_TERM'], 'lang': w['L_LANG']}
        for w in words
        if not pd.isnull(w['T_TERM']) and not pd.isnull(w['L_LANG'])
    ]

    data.append({
        'datasetCode': dataset_code,
        'definitions': definitions,
        'words': words,
    })

output_dir.mkdir(parents=True, exist_ok=True)

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)