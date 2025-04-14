import pandas as pd
import json
from collections import defaultdict

#input
file_path = "files/input/keeltega_estermist.xlsx"
sources_csv = "files/input/estermi_allikad.csv"
words_already_in_dataset = "files/input/estermi_s6nad.csv"

#output
meaning_notes_json = "files/output/meaning_notes.json" #notes - those without value should be deleted afterwards
meanings_to_ekilex_json = "files/output/meanings_to_ekilex.json" #will be saved to dataset
meanings_with_missing_sources_json = "files/output/meanings_with_missing_sources.json" #will not be saved to dataset
meanings_with_suspicious_words_json = "files/output/meanings_with_suspicious_words.json" #will not be saved to dataset

def map_languages(code):
    lang_map = {
        "fr": "fra", "de": "deu", "fi": "fin", "la": "lat",
        "en": "eng", "da": "dan", "it": "ita", "sv": "sve",
        "ru": "rus", "vn": "rus", "nl": "nld", "es": "spa",
        "pt": "por", "lv": "lat", "lt": "lit", "pr": "fra",
        "et": "est", "sw": "sve"
    }
    return lang_map.get(code, code)

def read_input_files(file_path, sources_csv, words_already_in_dataset):

    df = pd.read_excel(file_path)
    df.columns = df.columns.str.strip()

    required_columns = {"meaning_id", "meaning_note_id", "value"}
    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    df_sources = pd.read_csv(sources_csv, delimiter=';', dtype=str)
    source_mapping = {row["name"]: row["id"] for _, row in df_sources.iterrows()}

    existing_words_df = pd.read_csv(words_already_in_dataset, sep=";", quotechar='"', dtype=str)
    existing_words_df.columns = existing_words_df.columns.str.strip()

    existing_word_set = set()

    for _, row in existing_words_df.iterrows():
        id_val = row.get("id")
        word_val = row.get("value")
        lang_val = row.get("lang")

        if pd.isna(id_val) or pd.isna(word_val) or pd.isna(lang_val):
            continue

        existing_word_set.add((str(id_val).strip(), str(word_val).strip(), str(lang_val).strip()))

    return existing_words_df, existing_word_set, source_mapping, df

existing_words_df, existing_word_set, source_mapping, df = read_input_files(file_path, sources_csv, words_already_in_dataset)

meanings_to_ekilex = []
skipped_meanings = []

def parse_meaning(row):
    meaning_id = row["meaning_id"]
    note_id = row["meaning_note_id"]
    text = str(row["value"]).strip()

    initial_note = text
    words = []
    text = str(text).strip()

    last_bracket_pos = text.rfind("]")

    if last_bracket_pos != -1 and last_bracket_pos < len(text) - 1:
        text = text[:last_bracket_pos + 1].strip()

    entries = text.split("\n")

    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue

        parts = entry.split(":", 1)
        if len(parts) != 2:
            continue

        lang_code = parts[0].strip().lower()
        mapped_lang = map_languages(lang_code)


        word_and_sourcelinks = parts[1].strip()
        first_bracket_index = word_and_sourcelinks.find("[")

        if first_bracket_index == -1:
            words_list = [word_and_sourcelinks.strip()]
            sources = []
        else:
            words_list = word_and_sourcelinks[:first_bracket_index].strip().split(";")
            sources = word_and_sourcelinks[first_bracket_index:].strip()

        words_list = [word.strip() for word in words_list if word]

        separate_sources = sources.split("[") if sources else []
        sourcelink_values = [s.strip().strip("]") for s in separate_sources if s.strip()]

        for word in words_list:
            sourcelinks = [
                {
                    "sourceId": source_mapping.get(source, None),
                    "value": source,
                    "sourcelinkName": None
                }
                for source in sourcelink_values
            ] if sourcelink_values else []

            words.append({
                "valuePrese": word,
                "lang": mapped_lang,
                "lexemeValueStateCode": None,
                "public": True,
                "wordTypeCodes": [],
                "usages": [],
                "lexemeNotes": [],
                "lexemeSourceLinks": sourcelinks
            })

    return {
        "meaning_id": meaning_id,
        "meaning_note_id": note_id,
        "words": words,
        "note_value": initial_note,
        "skipped_words": []
    }


def merge_duplicate_words(words):
    merged = {}

    for word in words:
        key = (word["valuePrese"], word["lang"])
        if key not in merged:
            merged[key] = word
        else:
            print(words)
            merged[key]["lexemeSourceLinks"].extend(word["lexemeSourceLinks"])

    return list(merged.values())

# Process all meanings

initial_meanings = [
    parsed for _, row in df.iterrows()
    if (parsed := parse_meaning(row)) is not None
]

meanings_to_ekilex = []
skipped_meanings_no_sourcelink = []
skipped_meanings_suspicious_words = []

for meaning in initial_meanings:
    processed_words = []
    skip_due_to_suspicious = False

    for w in meaning["words"]:
        word_value = w["valuePrese"]

        if word_value.startswith('der '):
            normalized_word = word_value.replace('der ', '', 1)
            lexeme_note_value = 'der'
        elif word_value.startswith('die '):
            normalized_word = word_value.replace('die ', '', 1)
            lexeme_note_value = 'die'
        elif word_value.startswith('das '):
            normalized_word = word_value.replace('das ', '', 1)
            lexeme_note_value = 'das'
        else:
            normalized_word = word_value
            lexeme_note_value = None

        if len(normalized_word) > 30 or '-' in normalized_word:
            skip_due_to_suspicious = True
            break

        if (meaning["meaning_id"], normalized_word, w["lang"]) in existing_word_set:
            continue

        lexeme_notes = [{
            "value": lexeme_note_value,
            "valuePrese": lexeme_note_value,
            "lang": "deu",
            "complexity": "DETAIL",
            "public": False
        }] if lexeme_note_value else []

        w["valuePrese"] = normalized_word
        w["lexemeNotes"] = lexeme_notes

        processed_words.append(w)

    processed_words = merge_duplicate_words(processed_words)

    has_unknown_source = any(
        any(link["sourceId"] is None for link in word["lexemeSourceLinks"])
        for word in processed_words
    )

    entry = {
        "meaningId": meaning["meaning_id"],
        "datasetCode": "esterm",
        "words": processed_words,
        "notes": [{"id": meaning["meaning_note_id"], "value": meaning["note_value"]}]
    }

    if skip_due_to_suspicious:
        skipped_meanings_suspicious_words.append(entry)
    elif has_unknown_source:
        skipped_meanings_no_sourcelink.append(entry)
    else:
        meanings_to_ekilex.append(entry)


with open(meanings_to_ekilex_json, "w", encoding="utf-8") as f:
    json.dump(meanings_to_ekilex, f, indent=4, ensure_ascii=False)

with open(meanings_with_suspicious_words_json, "w", encoding="utf-8") as f:
    json.dump(skipped_meanings_suspicious_words, f, indent=4, ensure_ascii=False)

with open(meanings_with_missing_sources_json, "w", encoding="utf-8") as f:
    json.dump(skipped_meanings_no_sourcelink, f, indent=4, ensure_ascii=False)

print(f"Valid meanings: {len(meanings_to_ekilex)} meanings")
print(f"Meanings with suspicious words: {len(skipped_meanings_suspicious_words)} meanings")
print(f"Meanings with missing sources: {len(skipped_meanings_no_sourcelink)} meanings")


total_from_excel = len(df)
total_from_jsons = (
    len(meanings_to_ekilex) +
    len(skipped_meanings_suspicious_words) +
    len(skipped_meanings_no_sourcelink)
)

print(f"Total from Excel: {total_from_excel}")
print(f"Total from JSONs: {total_from_jsons}")
print("Match!" if total_from_excel == total_from_jsons else "Mismatch!")
