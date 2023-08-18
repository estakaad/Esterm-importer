import requests
import json
from dotenv import load_dotenv
import os
import re


load_dotenv()
api_key = os.environ.get("API_KEY")
parameters = {}
crud_role_dataset = os.environ.get("ESTERM")

header = {"ekilex-api-key": api_key}
parameters = {"crudRoleDataset": crud_role_dataset}


# Function to check if an object is already present in the application
def is_present(source):
    value_texts = [prop['valueText'] for prop in source['sourceProperties'] if prop['type'] == 'SOURCE_NAME']

    first_word = re.search(r'\b\w+\b', value_texts[0])

    if not first_word:
        print(f"No suitable word found in the valueText for source {value_texts[0]}")
        return False

    search_value = '*' + first_word.group() + '*'

    endpoint = f"https://ekitest.tripledev.ee/ekilex/api/source/search/{search_value}"  # Use the modified search value
    response = requests.get(endpoint, headers=header, params=parameters)

    if response.status_code >= 200 and response.status_code < 300:
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            print(f"Failed to parse JSON from response for source {value_texts[0]}. Response text: {response.text}")
            return False

        for source_response in response_data:
            if set(value_texts).issubset(set(source_response['sourceNames'])):
                return True
    else:
        print(f"Received non-200 response for source {value_texts[0]}. Status code: {response.status_code}, Response text: {response.text}")

    return False


def create_source(source):
    endpoint = "https://ekitest.tripledev.ee/ekilex/api/source/create"
    response = requests.post(endpoint, headers=header, params=parameters, json=source)
    if response.status_code >= 200 and response.status_code < 300:
        try:
            response_data = response.json()
            print(response_data)
            print(response_data['id'])
            return response_data['id']
        except json.JSONDecodeError:
            print(f"Failed to parse JSON from response when creating source {source['sourceProperties'][0]['valueText']}. Response text: {response.text}")
            return None
    else:
        print(f"Received non-200 response when creating source {source['sourceProperties'][0]['valueText']}. Status code: {response.status_code}, Response text: {response.text}")
        return None


def get_source_id(source):
    value_texts = [prop['valueText'] for prop in source['sourceProperties'] if prop['type'] == 'SOURCE_NAME']

    first_word = re.search(r'\b\w+\b', value_texts[0])
    if not first_word:
        print(f"No suitable word found in the valueText for source {value_texts[0]}")
        return None

    search_value = '*' + first_word.group() + '*'

    endpoint = f"https://ekitest.tripledev.ee/ekilex/api/source/search/{search_value}"
    response = requests.get(endpoint, headers=header, params=parameters)

    if response.status_code >= 200 and response.status_code < 300:
        try:
            response_data = response.json()
            for source_response in response_data:
                if set(value_texts).issubset(set(source_response['sourceNames'])):
                    return source_response['id']
        except (json.JSONDecodeError, IndexError):
            print(f"Failed to retrieve the ID of the source {value_texts[0]}. Response text: {response.text}")
            return None
    else:
        print(f"Received non-200 response when retrieving the ID of the source {value_texts[0]}. Status code: {response.status_code}, Response text: {response.text}")
        return None



def check_sources_from_ekilex(file):
    sources = json.load(file)
    updated_sources = []

    for source in sources:
        source_id = None
        if is_present(source):
            print(f"Source with name {source['sourceProperties'][0]['valueText']} is already present in the application.")
            source_id = get_source_id(source)
        else:
            print(f"Source with name {source['sourceProperties'][0]['valueText']} is not present in the application.")
            print(source)
            source_id = create_source(source)

        if source_id:
            updated_source = {'id': source_id}
            updated_source.update(source)
            updated_sources.append(updated_source)

    with open('files/output/sources_with_ids.json', 'w', encoding='utf-8') as file:
        json.dump(updated_sources, file, ensure_ascii=False, indent=4)

    return updated_sources



