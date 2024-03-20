import json
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def get_avi_ids():
    file_path = 'files/import/esterm-test-05-03 - SELLEST PROOVIKS LIVEDA/concepts_with_word_ids.json'

    avi_concept_ids = []

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            for entry in data:
                if 'domains' in entry:
                    for d in entry['domains']:
                        if 'TR8' in d['code']:
                            # print(entry['conceptIds'])
                            avi_concept_ids.append(entry['conceptIds'][0])
                if 'notes' in entry:
                    for n in entry['notes']:
                        if n['value'].startswith('Valdkond ICAO'):
                            # print(entry['conceptIds'])
                            avi_concept_ids.append(entry['conceptIds'][0])
                        elif n['value'].startswith('Tunnus'):
                            if 'LENNUNDUS' in n['value']:
                                # print(entry['conceptIds'])
                                avi_concept_ids.append(entry['conceptIds'][0])
                        elif n['value'].startswith('Päritolu'):
                            if 'LTB' in n['value']:
                                avi_concept_ids.append(entry['conceptIds'][0])

    except FileNotFoundError:
        print("The file was not found. Please check the file path.")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON at position {e.pos}: {e.msg}")

    unique_list = []

    for item in avi_concept_ids:
        if item not in unique_list:
            unique_list.append(item)

    print(len(unique_list))
    print(unique_list)

def load_and_lookup():
    old_ids_path = 'files/import/esterm-live-avi-20-03/avi_ids.json'
    saved_file_path = 'files/import/esterm-live-avi-20-03/concepts_saved.json'

    old_ids = []  # Initialize as an empty list, not a dictionary
    concepts_saved = {}

    # Load old_ids from avi_ids.json
    try:
        with open(old_ids_path, 'r', encoding='utf-8') as file:
            old_ids = json.load(file)  # Expecting a list here
    except FileNotFoundError:
        print(f"File not found: {old_ids_path}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {old_ids_path}: {e}")

    # Load concepts_saved from concepts_saved.json
    try:
        with open(saved_file_path, 'r', encoding='utf-8') as file:
            concepts_saved = json.load(file)
    except FileNotFoundError:
        print(f"File not found: {saved_file_path}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {saved_file_path}: {e}")

    results = []

    for concept in concepts_saved:
        if 'conceptIds' in concept and concept['conceptIds']:  # Ensure conceptIds is not empty
            # Check if the first ID in concept['conceptIds'] is in old_ids list
            if concept['conceptIds'][0] in old_ids:
                results.append(concept['id'])

    return results

def save_results(results, filename):
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(results, file, ensure_ascii=False, indent=4)
        print(f"Results saved to {filename}")
    except Exception as e:
        print(f"Error saving results to {filename}: {e}")

#lookup_results = load_and_lookup()
#save_results(lookup_results, 'files/import/esterm-live-avi-20-03/avi_concepts_ids_ekilex_live.json')


def set_up_requests(dataset, environment):
    api_key = os.environ.get("API_KEY")
    parameters = {"crudRoleDataset": dataset}
    headers = {"ekilex-api-key": api_key}
    base_url = os.environ.get(environment)
    return parameters, headers, base_url

session = requests.Session()

def get_avi_concepts(ids_path, dataset, environment):
    parameters, headers, base_url = set_up_requests(dataset, environment)

    with open(ids_path, 'r') as file:
        ids = json.load(file)

    responses = []

    for id in ids:
        response = session.get(f'{base_url}/api/term-meaning/details/{id}/{dataset}', params=parameters, headers=headers)
        print(f"Requesting URL: {response.request.url}")
        if response.status_code == 200:
            responses.append(response.json())
        else:
            print(f"Failed to get data for ID {id}")

    output_file = 'files/import/esterm-live-avi-20-03/avi_concepts_from_ekilex.json'

    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(responses, file, ensure_ascii=False, indent=4)

# Usage
ids_path = 'files/import/esterm-live-avi-20-03/avi_concepts_ids_ekilex_live.json'
get_avi_concepts(ids_path, 'est_test', 'LIVE')