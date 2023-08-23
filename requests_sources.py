import requests
import json
from dotenv import load_dotenv
import os
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
    endpoint = "https://ekitest.tripledev.ee/ekilex/api/source/search"

    for value_text in value_texts:
        params = {"crudRoleDataset": crud_role_dataset, "query": value_text}
        response = requests.get(endpoint, headers=header, params=params)

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


# Try getting existing source's ID, if source doesn't exist, create a new one and return its ID.
# If source already existed, return False. If source was created, return True.
def get_or_create_source(source):
    existing_id = get_existing_source_id(source)
    if existing_id:
        return existing_id, False
    new_id = create_source(source)
    if new_id:
        logger.info(
            f"Created new source with ID {new_id} and name {source['sourceProperties'][0]['valueText']}.")
    return new_id, True


def assign_ids_to_all_sources(input_file):

    sources_with_ids_file = 'files/output/sources_with_ids.json'
    ids_of_created_sources_file = 'files/output/ids_of_created_sources.json'
    updated_sources = []
    ids_of_created_sources = []

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        for source in data:
            source_id, was_created = get_or_create_source(source)
            if source_id:
                ordered_source = OrderedDict([('id', source_id)] + list(source.items()))
                updated_sources.append(ordered_source)
                if was_created:
                    ids_of_created_sources.append(source_id)

    # Create a file with sources and their ID-s
    with open(sources_with_ids_file, 'w', encoding='utf-8') as f:
        json.dump(updated_sources, f, ensure_ascii=False, indent=4)

    # Create a file with list of ID-s of created sources
    with open(ids_of_created_sources_file, 'w', encoding='utf-8') as f:
        json.dump(ids_of_created_sources, f, ensure_ascii=False, indent=4)

    return updated_sources


def delete_created_sources(file):
    with open(file, 'r', encoding='utf-8') as file:
        source_ids = json.load(file)

    endpoint = "https://ekitest.tripledev.ee/ekilex/api/source/delete"

    for source_id in source_ids:
        params = {
            'sourceId': source_id,
            'crudRoleDataset': crud_role_dataset
        }

        response = requests.delete(endpoint, headers=header, params=params)

        if response.status_code >= 200 and response.status_code < 300:
            logger.info(f"Successfully deleted source with ID {source_id}.")
        else:
            logger.info(f"Failed to delete source with ID {source_id}. Status code: {response.status_code}, "
                        f"Response text: {response.text}")