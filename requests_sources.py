import requests
import json
from dotenv import load_dotenv
import os
import re
import log_config
from collections import OrderedDict


logger = log_config.get_logger()


load_dotenv()
api_key = os.environ.get("API_KEY")
parameters = {}
crud_role_dataset = os.environ.get("ESTERM")

header = {"ekilex-api-key": api_key}
parameters = {"crudRoleDataset": crud_role_dataset}


def get_existing_source_id(source):
    value_texts = [prop['valueText'] for prop in source['sourceProperties'] if prop['type'] == 'SOURCE_NAME']

    for value_text in value_texts:
        endpoint = f"https://ekitest.tripledev.ee/ekilex/api/source/search/{value_text}"
        response = requests.get(endpoint, headers=header, params=parameters)

        if response.status_code >= 200 and response.status_code < 300:
            try:
                response_data = response.json()
                for source_response in response_data:
                    # Check if all elements in value_texts are present in source_response['sourceNames']
                    if all(text in source_response['sourceNames'] for text in value_texts):
                        return source_response['id']
            except (json.JSONDecodeError, IndexError):
                logger.warning(f"Failed to retrieve the ID of the source {value_texts[0]}. "
                               f"Response text: {response.text}")
        else:
            logger.warning(f"Received non-200 response when retrieving the ID of the source {value_texts[0]}. "
                           f"Status code: {response.status_code}, Response text: {response.text}")
    return None


# Create a new source in Ekilex and return its ID
def create_source(source):
    endpoint = "https://ekitest.tripledev.ee/ekilex/api/source/create"
    response = requests.post(endpoint, headers=header, params=parameters, json=source)

    if response.status_code >= 200 and response.status_code < 300:
        try:
            response_data = response.json()
            return response_data['id']
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON from response when creating source "
                           f"{source['sourceProperties'][0]['valueText']}. Response text: {response.text}")
    else:
        logger.warning(f"Received non-200 response when creating source {source['sourceProperties'][0]['valueText']}. "
                       f"Status code: {response.status_code}, Response text: {response.text}")
    return None


# Try getting existing source's ID, if source doesn't exist, create a new one and return its ID
def get_or_create_source(source):
    existing_id = get_existing_source_id(source)
    if existing_id:
        return existing_id
    return create_source(source)


def assign_ids_to_all_sources(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        new_data = []
        for source in data:
            source_id = get_or_create_source(source)
            if source_id:
                ordered_source = OrderedDict([('id', source_id)] + list(source.items()))
                new_data.append(ordered_source)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=4)