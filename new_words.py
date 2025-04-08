import pandas as pd
import json
from collections import defaultdict

# File paths
file_path = "files/input/keeltega_estermist.xlsx"
sources_csv = "files/input/estermi_allikad.csv"
meaning_notes_json = "files/output/meaning_notes.json"
structured_meanings_json = "files/output/structured_meanings.json"
skipped_meanings_json = "files/output/skipped_meanings.json"

# Language mapping function
def map_languages(code):
    lang_map = {
        "fr": "fra", "de": "deu", "fi": "fin", "la": "lat",
        "en": "eng", "da": "dan", "it": "ita", "sv": "sve",
        "ru": "rus", "vn": "rus", "nl": "nld", "es": "spa",
        "pt": "por", "lv": "lat", "lt": "lit", "pr": "fra",
        "et": "est", "sw": "sve"
    }
    return lang_map.get(code, code)

# Read the Excel file
df = pd.read_excel(file_path)
df.columns = df.columns.str.strip()  # Remove extra spaces

# Ensure required columns exist
required_columns = {"meaning_id", "meaning_note_id", "value"}
missing_columns = required_columns - set(df.columns)
if missing_columns:
    raise ValueError(f"Missing required columns: {missing_columns}")

# Read sources CSV
df_sources = pd.read_csv(sources_csv, delimiter=';', dtype=str)
source_mapping = {row["name"]: row["id"] for _, row in df_sources.iterrows()}

# Load already existing words (destination content)
existing_words_df = pd.read_csv("files/input/olemasolevad_samas_keeles.csv", sep=";", quotechar='"', dtype=str)
existing_words_df.columns = existing_words_df.columns.str.strip()  # Clean column names
print(existing_words_df.head())

# Print column names for debugging
print("Columns in existing_words_df:", existing_words_df.columns.tolist())

# Create a lookup set for filtering
existing_word_set = set(
    (row["id"], row["value"].strip(), row["lang"].strip())
    for _, row in existing_words_df.iterrows()
)


meaning_notes = []  # Stores meaning notes separately
structured_meanings = []  # Stores structured data
skipped_meanings = []  # Stores meanings with unknown sources or invalid language codes

def parse_value(meaning_id, note_id, text):

    words = []
    note_value = None
    text = str(text).strip()

    # Extract text after the last ']' as a note if applicable
    last_bracket_pos = text.rfind("]")
    if last_bracket_pos != -1 and last_bracket_pos < len(text) - 1:
        note_value = text[last_bracket_pos + 1:].strip()
        text = text[:last_bracket_pos + 1].strip()

    entries = text.split("\n")  # Split by newlines to separate different language entries

    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue

        parts = entry.split(":", 1)  # Split by colon to get language and word-source section
        if len(parts) != 2:
            continue  # Skip malformed entries

        lang_code = parts[0].strip().lower()  # Extract language code
        mapped_lang = map_languages(lang_code)

        # Skip this meaning if language code is not exactly three characters long
        if len(mapped_lang) != 3:
            return None

        word_and_sourcelinks = parts[1].strip()  # Extract words and sources

        first_bracket_index = word_and_sourcelinks.find("[")
        if first_bracket_index == -1:
            words_list = [word_and_sourcelinks.strip()]  # No sources found
            sources = []
        else:
            words_list = word_and_sourcelinks[:first_bracket_index].strip().split(";")  # Split words
            sources = word_and_sourcelinks[first_bracket_index:].strip()  # Extract sources

        words_list = [word.strip() for word in words_list if word]  # Clean up spaces

        separate_sources = sources.split("[") if sources else []
        sourcelink_values = [s.strip().strip("]") for s in separate_sources if s.strip()]

        word_entries = []
        for word in words_list:
            if not (word and len(word) > 30 and ' - ' in word):
                # Skip word if it already exists in destination
                if (str(meaning_id), word, mapped_lang) in existing_word_set:
                    continue

                sourcelinks = [
                    {
                        "sourceId": source_mapping.get(source, None),
                        "value": source,
                        "sourcelinkName": None
                    }
                    for source in sourcelink_values
                ] if sourcelink_values else []

                word_entries.append({
                    "valuePrese": word,
                    "lang": mapped_lang,
                    "lexemeValueStateCode": None,
                    "public": True,
                    "wordTypeCodes": [],
                    "usages": [],
                    "lexemeNotes": [],
                    "lexemeSourceLinks": sourcelinks
                })

        words.extend(word_entries)

    return {
        "meaning_id": meaning_id,
        "meaning_note_id": note_id,
        "words": words,
        "note_value": note_value if note_value else None
    }

# Process all meanings
for _, row in df.iterrows():
    parsed = parse_value(row["meaning_id"], row["meaning_note_id"], row["value"])

    # Skip if parsing returned None (invalid language code)
    if parsed is None:
        continue

    # Save meaning notes separately
    meaning_notes.append({
        "meaning_note_id": parsed["meaning_note_id"],
        "value": parsed["note_value"]
    })

    # Check if any word has an unknown source ID
    has_unknown_source = any(
        any(sourcelink["sourceId"] is None for sourcelink in word["lexemeSourceLinks"])
        for word in parsed["words"]
    )

    structured_entry = {
        "meaningId": parsed["meaning_id"],
        "datasetCode": "esterm",
        "words": parsed["words"],
        "notes": [ {
            "id": parsed["meaning_note_id"],
            "value": row["value"],
            "valuePrese": row["value"],
            "publicity": False
        }] if parsed["meaning_note_id"] else []
    }

    if has_unknown_source:
        skipped_meanings.append(structured_entry)
    else:
        structured_meanings.append(structured_entry)

# Save meaning notes JSON
with open(meaning_notes_json, "w", encoding="utf-8") as f:
    json.dump(meaning_notes, f, indent=4, ensure_ascii=False)

# Save structured meanings JSON (only valid sources)
with open(structured_meanings_json, "w", encoding="utf-8") as f:
    json.dump(structured_meanings, f, indent=4, ensure_ascii=False)

# Save skipped meanings JSON
with open(skipped_meanings_json, "w", encoding="utf-8") as f:
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
print("Count of different language words in structured meanings:")
for lang, count in sorted(language_counts.items()):
    print(f"  {lang}: {count}")

print(f"Meaning notes JSON saved to {meaning_notes_json}")
print(f"Structured meanings JSON saved to {structured_meanings_json}")
print(f"Skipped meanings JSON saved to {skipped_meanings_json}")
