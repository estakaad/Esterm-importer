import pandas as pd
import json
from collections import defaultdict

#input
file_path = "files/input/keeltega_estermist.xlsx"
sources_csv = "files/input/estermi_allikad.csv"
words_already_in_dataset = "files/input/estermi_s6nad.csv"

#output
meaning_notes_json = "files/output/meaning_notes.json" #notes - those without value should be deleted afterwards
structured_meanings_json = "files/output/meanings_to_ekilex.json" #will be saved to dataset
meanings_to_be_reviewed_json = "files/output/meanings_to_be_reviewed.json" #will not be saved to dataset

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


#meaning_notes = []  # Stores meaning notes separately
structured_meanings = []  # Stores structured data
skipped_meanings = []  # Stores meanings with unknown sources or invalid language codes

def parse_value(meaning_id, note_id, text):

    words = []
    skipped_words = []
    text = str(text).strip()

    last_bracket_pos = text.rfind("]")
    if last_bracket_pos != -1 and last_bracket_pos < len(text) - 1:
        text = text[:last_bracket_pos + 1].strip()

    entries = text.split("\n")

    #handle one language entry with sourcelink:
    # DE: seine Tätigkeit aufnehmen [WPG-1448]
    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue

        parts = entry.split(":", 1)
        if len(parts) != 2:
            continue

        lang_code = parts[0].strip().lower()
        mapped_lang = map_languages(lang_code)

        if len(mapped_lang) != 3:
            return None

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

        word_entries = []
        for word in words_list:

            # skip words which probably contain a definition
            if word and len(word) > 30 and ' - ' in word:
                skipped_words.append(word)
                continue

            # skip words which already exist in the dataset for this particular meaning
            if (str(meaning_id), word, mapped_lang) in existing_word_set:
                print(word)
                continue

            # remove german articles, add them as separate lexeme notes to handle in the future
            if word.startswith('der '):
                word = word.replace('der ', '')
                lexeme_note_value = 'der'
            elif word.startswith('die '):
                word = word.replace('die ', '')
                lexeme_note_value = 'die'
            elif word.startswith('das '):
                word = word.replace('das ', '')
                lexeme_note_value = 'das'
            else:
                lexeme_note_value = None

            sourcelinks = [
                {
                    "sourceId": source_mapping.get(source, None),
                    "value": source,
                    "sourcelinkName": None
                }
                for source in sourcelink_values
            ] if sourcelink_values else []

            lexeme_notes = [
                {
                    "value": lexeme_note_value,
                    "public": False,
                    "lang": "deu"
                }
            ] if lexeme_note_value else []

            word_entries.append({
                "valuePrese": word,
                "lang": mapped_lang,
                "lexemeValueStateCode": None,
                "public": True,
                "wordTypeCodes": [],
                "usages": [],
                "lexemeNotes": lexeme_notes,
                "lexemeSourceLinks": sourcelinks
            })

        words.extend(word_entries)

    return {
        "meaning_id": meaning_id,
        "meaning_note_id": note_id,
        "words": words,
        "note_value": text,
        "skipped_words": skipped_words
    }


# Process all meanings
for _, row in df.iterrows():
    parsed = parse_value(row["meaning_id"], row["meaning_note_id"], row["value"])

    if parsed is None:
        continue

    # meaning_notes.append({
    #     "meaning_note_id": parsed["meaning_note_id"],
    #     "value": parsed["note_value"]
    # })

    has_unknown_source = any(
        any(sourcelink["sourceId"] is None for sourcelink in word["lexemeSourceLinks"])
        for word in parsed["words"]
    )

    # Determine final note value depending on meaning status
    is_skipped = any(
        any(sourcelink["sourceId"] is None for sourcelink in word["lexemeSourceLinks"])
        for word in parsed["words"]
    )

    structured_entry = {
        "meaningId": parsed["meaning_id"],
        "datasetCode": "esterm",
        "words": parsed["words"],
        "notes": [{
            "id": parsed["meaning_note_id"],
            "value": row["value"],
            "valuePrese": row["value"],
            "publicity": False
        }] if parsed["meaning_note_id"] else []
    }

    # 1. Completely skipped (no words)
    if not parsed["words"]:
        skipped_meanings.append(structured_entry)

    # 2. All source links are valid, and some words are skipped
    elif parsed["skipped_words"]:
        structured_meanings.append(structured_entry)
        skipped_meanings.append(structured_entry)

    # 3. Valid, no skipped words, all source links are known
    elif not has_unknown_source:
        structured_meanings.append(structured_entry)

    # 4. Valid words but unknown source links → only skipped
    else:
        skipped_meanings.append(structured_entry)

#
# # Save meaning notes JSON
# with open(meaning_notes_json, "w", encoding="utf-8") as f:
#     json.dump(meaning_notes, f, indent=4, ensure_ascii=False)

# Save structured meanings JSON (only valid sources)
with open(structured_meanings_json, "w", encoding="utf-8") as f:
    json.dump(structured_meanings, f, indent=4, ensure_ascii=False)

# Save skipped meanings JSON
with open(meanings_to_be_reviewed_json, "w", encoding="utf-8") as f:
    json.dump(skipped_meanings, f, indent=4, ensure_ascii=False)

# Calculate statistics
total_meanings = len(structured_meanings)
skipped_meanings_count = len(skipped_meanings)
total_words = sum(len(entry["words"]) for entry in structured_meanings)

# Count words per language
language_counts = defaultdict(int)
for entry in structured_meanings:
    for word in entry["words"]:
        language_counts[word["lang"]] += 1

# Print statistics
print(f"Count of meanings in structured meanings: {total_meanings}")
print(f"Count of meanings in skipped meanings: {skipped_meanings_count}")
print(f"Total count of words in structured meanings: {total_words}")

#print("Count of different language words in structured meanings:")
#
#for lang, count in sorted(language_counts.items()):
#    print(f"  {lang}: {count}")

#print(f"Meaning notes JSON saved to {meaning_notes_json}")
print(f"Structured meanings JSON saved to {structured_meanings_json}")
print(f"Skipped meanings JSON saved to {meanings_to_be_reviewed_json}")
