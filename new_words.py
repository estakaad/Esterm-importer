import pandas as pd
import json
import re

file_path = "files/input/keeltega_estermist.xlsx"
sources_csv = "files/input/estermi_allikad.csv"
output_json = "files/output/keeltega_estermist.json"
unique_sources_json = "files/output/unique_sources.json"
updated_sources_json = "files/output/updated_unique_sources.json"

def map_languages(code):
    lang_map = {
        "fr": "fra", "de": "deu", "fi": "fin", "la": "lat",
        "en": "eng", "da": "dan", "it": "ita", "sv": "sve",
        "ru": "rus", "vn": "rus", "nl": "nld", "es": "spa",
        "pt": "por", "lv": "lat", "lt": "lit", "pr": "fra",
        "et": "est", "sw": "sve"
    }
    return lang_map.get(code, code)

df = pd.read_excel(file_path)

unique_sources = set()

def parse_value(meaning_id, text):
    words = []
    entries = re.split(r'\n|;', text)

    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue

        match = re.match(r'([A-Z]{2}):\s*(.+)', entry)
        if match:
            lang = match.group(1).lower()
            remaining_text = match.group(2).strip()

            words_list = re.split(r'\s*\[[^\]]*\]', remaining_text)
            source_links = re.findall(r'\[(.*?)\]', remaining_text)

            for source in source_links:
                unique_sources.add(source)

            formatted_sourcelinks = []
            for source in source_links:
                if source.startswith("WPG-"):
                    sourcelinkname = source[4:]
                    formatted_sourcelinks.append({
                        "sourceId": None,
                        "value": "WPG",
                        "sourcelinkName": sourcelinkname
                    })
                elif source.startswith("GG008-"):
                    sourcelinkname = source[6:]
                    formatted_sourcelinks.append({
                        "sourceId": None,
                        "value": "GG008",
                        "sourcelinkName": sourcelinkname
                    })
                elif source.startswith("EUR,"):
                    sourcelinkname = source[4:]
                    formatted_sourcelinks.append({
                        "sourceId": None,
                        "value": "EUR",
                        "sourcelinkName": sourcelinkname.strip()
                    })
                elif source.startswith("ENE,"):
                    sourcelinkname = source[4:]
                    formatted_sourcelinks.append({
                        "sourceId": None,
                        "value": "ENE",
                        "sourcelinkName": sourcelinkname.strip()
                    })
                elif source.startswith("2670,"):
                    sourcelinkname = source[5:]
                    formatted_sourcelinks.append({
                        "sourceId": None,
                        "value": "2670",
                        "sourcelinkName": sourcelinkname.strip()
                    })
                else:
                    formatted_sourcelinks.append({
                        "sourceId": None,
                        "value": source,
                        "sourcelinkName": None
                    })

            for word in words_list:
                word = word.strip()
                if word:
                    words.append({
                        "value": word,
                        "lang": map_languages(lang),
                        "sourcelinks": formatted_sourcelinks
                    })

    return {
        "meaningid": meaning_id,
        "words": words
    }

# Convert all rows
result = [parse_value(row["id"], row["value"]) for _, row in df.iterrows()]

# Convert unique sources into structured JSON
unique_sources_list = [{"name": source, "sourceId": None} for source in sorted(unique_sources)]

# Save parsed words JSON
with open(output_json, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=4, ensure_ascii=False)

# Save unique sources JSON (before matching with source IDs)
with open(unique_sources_json, "w", encoding="utf-8") as f:
    json.dump(unique_sources_list, f, indent=4, ensure_ascii=False)

# Load sources CSV
df_sources = pd.read_csv(sources_csv, delimiter=';', dtype=str)

# Create a mapping of source name → sourceId
source_mapping = {row["name"]: row["id"] for _, row in df_sources.iterrows()}

# Update sourceId if a match is found in source_mapping
for source in unique_sources_list:
    source_name = source["name"]
    if source_name in source_mapping:
        source["sourceId"] = source_mapping[source_name]

sourcelink_values_without_matches = []

for entry in result:
    for word in entry["words"]:
        for sourcelink in word["sourcelinks"]:
            sourcelink["sourceId"] = source_mapping.get(sourcelink["value"], None)
            if sourcelink["sourceId"] is None:
                sourcelink_values_without_matches.append(sourcelink["value"])

sourcelink_values_without_matches_unique = set(sourcelink_values_without_matches)
print(sourcelink_values_without_matches_unique)
print(str(len(sourcelink_values_without_matches_unique)))

with open(updated_sources_json, "w", encoding="utf-8") as f:
    json.dump(unique_sources_list, f, indent=4, ensure_ascii=False)

with open(output_json, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=4, ensure_ascii=False)

print(f"JSON data saved to {output_json}")
print(f"Unique sources saved to {updated_sources_json}")
