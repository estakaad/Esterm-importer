import string
import json
import time
import logging
from datetime import timedelta
from datetime import datetime
import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("API_KEY")

base_data = 'failid/andmestik/keelevaraga/ekilex_import_data_inter.json'
type = 'inter'

current_datetime = datetime.now()

# Format the datetime object as a string
formatted_datetime = current_datetime.strftime("%Y-%m-%d_%H-%M-%S")
output_directory = f'output/{formatted_datetime}'
os.makedirs(output_directory, exist_ok=True)

# Initialize logging and other variables
start_time = time.time()
logging.basicConfig(filename=f'{output_directory}/logfile_{formatted_datetime}.log', level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(message)s')

api_url = 'https://ekitest.tripledev.ee/ekilex/api/'

# Load the original JSON data
with open(base_data, 'r', encoding='utf-8') as f:
    data = json.load(f)

removed_items = []
filtered_data = []

for d in data:
    headword_value = d["headwordValue"]
    resp = requests.get(
        url=api_url + 'word/ids/' + headword_value + '/eki/est',
        headers={
            'ekilex-api-key': api_key,
            'Content-type': 'application/json',
            'Accept': 'application/json'
        }
    )

    if resp.status_code == 200:
        response_data = resp.json()
        if response_data:
            filtered_data.append(d)
            logging.info(f"Word {headword_value} is present in ÜS")
        else:
            removed_items.append(d)
            logging.info(f"Object removed because word {headword_value} is not present in ÜS")


logging.info(f'Count of words in ÜS: {str(len(filtered_data))}')
logging.info(f'Count of words not in ÜS: {str(len(removed_items))}')

# Save the filtered data to a temporary JSON file
with open(f'{output_directory}/temp_filtered_data.json', 'w', encoding='utf-8') as f:
    json.dump(filtered_data, f, ensure_ascii=False)

# Save the removed items
with open(f'{output_directory}/words_not_in_ys.json', 'w', encoding='utf-8') as f:
    json.dump(removed_items, f, ensure_ascii=False, indent=2)

# Load the filtered JSON data
with open(f'{output_directory}/temp_filtered_data.json', 'r', encoding='utf-8') as f:
    filtered_data = json.load(f)

# Load other necessary files
with open('input/sagedusloendid.txt', 'r', encoding='utf-8') as f:
    frequency_words = set(line.strip() for line in f.readlines())

with open('input/blacklist.txt', 'r', encoding='utf-8') as f:
    words_to_be_ignored = set(line.strip() for line in f.readlines())

# Initialize variables
sanitized_data = filtered_data.copy()
removed_items = []

# Apply other rules for data sanitation
for d in filtered_data:
    headword_value = d["headwordValue"]
    words_to_remove = []
    removed_items_dict = {"headwordValue": headword_value, "synCandidateWords": []}

    # Apply your rules here (this is where your original code for rules 1-8 would go)
    for item in d["synCandidateWords"]:
        # 1. Kas tõlkevaste kandidaat sisaldab tühikut või sidekriipsu?
        if ' ' not in item['value'] and '-' not in item['value']:
            # Ära eemalda, kui sagedusloendis pole, aga kaal on suurem kui 0.8
            if item['weight'] > 0.8:
                continue
            # Kui tühikut ega sidekriipsu pole ja kaal pole suurem kui 0.8, siis kontrolli,
            # kas sõna on sagedusloendis. Kui ei ole, eemalda see.
            if item["value"] not in frequency_words:
                words_to_remove.append(item)
                removed_items_dict["synCandidateWords"].append(item)
                logging.info(
                    f"Eemaldatud: {item['value']}. Reegel nr 1")

        # 2. Kas tõlkevaste kandidaat on nimekirjas blacklist.txt?
        if item['value'] in words_to_be_ignored:
            has_kdictionary = False
            for definition in item['definitions']:
                for sourceLink in definition['sourceLinks']:
                    if sourceLink['value'] == 'KDictionary':
                        has_kdictionary = True
                        break  # leidis KDictionary, edasi pole vaja midagi kontrollida, need sõnad jäävad
                if has_kdictionary:
                    break
            if not has_kdictionary:  # eemalda, kui ühelgi definitsioonil pole KDictionary allikas
                words_to_remove.append(item)
                removed_items_dict["synCandidateWords"].append(item)
                logging.info(
                    f"Eemaldatud: {item['value']}. Reegel nr 2")

        # 3. Kas tõlkevaste kandidaat koosneb artiklist ja sõnast? Kui on ka ainult sõnast koosnev vaste, eemalda artikliga.
        if item['value'].lower().startswith('the '):
            word_without_article = item['value'][4:]  # remove 'the ' from the start
            if any(word_without_article == word['value'] for word in d["synCandidateWords"]):
                words_to_remove.append(item)
                removed_items_dict["synCandidateWords"].append(item)
                logging.info(
                    f"Eemaldatud: {item['value']}. Reegel nr 3")
            else:
                # 4. Kui tõlkevastest on ainult artikliga variant, siis eemalda artikkel, aga jäta sõna alles
                item['value'] = word_without_article
                logging.info(
                    f"Muudetud: {item['value']}. Reegel nr 4")

        if item['value'].lower().startswith('a '):
            word_without_article = item['value'][2:]
            if any(word_without_article == word['value'] for word in d["synCandidateWords"]):
                words_to_remove.append(item)
                removed_items_dict["synCandidateWords"].append(item)
                logging.info(
                    f"Eemaldatud: {item['value']}. Reegel nr 3")
            else:
                # 4. Kui tõlkevastest on ainult artikliga variant, siis eemalda artikkel, aga jäta sõna alles
                item['value'] = word_without_article
                logging.info(
                    f"Muudetud: {item['value']}. Reegel nr 4")

        if item['value'].lower().startswith('an '):
            word_without_article = item['value'][3:]
            if any(word_without_article == word['value'] for word in d["synCandidateWords"]):
                words_to_remove.append(item)
                removed_items_dict["synCandidateWords"].append(item)
                logging.info(
                    f"Eemaldatud: {item['value']}. Reegel nr 3")
            else:
                # 4. Kui tõlkevastest on ainult artikliga variant, siis eemalda artikkel, aga jäta sõna alles
                item['value'] = word_without_article
                logging.info(
                    f"Muudetud: {item['value']}. Reegel nr 4")

        # 5. Eemalda tõlkevasted, kui need on topelt (kui on value 'hello', eemalda vaste 'hello hello'
        words = item['value'].split()
        if len(words) > 1 and all(word == words[0] for word in words):
            words_to_remove.append(item)
            removed_items_dict["synCandidateWords"].append(item)
            logging.info(
                f"Eemaldatud: {item['value']}. Reegel nr 4")

        # 6. Eemalda tõlkevasted, kui need algavad koma ja tühikuga
        if any(item['value'].startswith(punct + " ") for punct in string.punctuation):
            words_to_remove.append(item)
            removed_items_dict["synCandidateWords"].append(item)
            logging.info(
                f"Eemaldatud: {item['value']}. Reegel nr 6")

        # 7. Eemalda tõlkevasted, kui need sisaldavad numbrit
        if any(char.isdigit() for char in item['value']):
            words_to_remove.append(item)
            removed_items_dict["synCandidateWords"].append(item)
            logging.info(
                f"Eemaldatud: {item['value']}. Reegel nr 7")

        # 8. Eemalda tõlkevasted, kui need sisaldavad "'s" või " 's"
        if " 's" in item['value']:
            words_to_remove.append(item)
            removed_items_dict["synCandidateWords"].append(item)
            logging.info(
                f"Eemaldatud: {item['value']}. Reegel nr 8")

    # Remove invalid translation candidates
    for item in words_to_remove:
        if item in d["synCandidateWords"]:
            d["synCandidateWords"].remove(item)

    # Add headword to removed translation candidates
    if removed_items_dict["synCandidateWords"]:
        removed_items.append(removed_items_dict)

sanitized_filename = f"{output_directory}/sanitised_data_{type}_{formatted_datetime}.json"
removed_filename = f"{output_directory}/removed_translation_candidates_{type}_{formatted_datetime}.json"

# Save the sanitized data
with open(sanitized_filename, 'w', encoding='utf-8') as f:
    json.dump(sanitized_data, f, ensure_ascii=False, indent=2)

# Save the removed items again, in case more were added
with open(removed_filename, 'w', encoding='utf-8') as f:
    json.dump(removed_items, f, ensure_ascii=False, indent=2)

# Calculate and print execution time
end_time = time.time()
execution_time = end_time - start_time

logging.info(f"The script ran for: {str(timedelta(seconds=execution_time))}")

print("Program has finished executing.")