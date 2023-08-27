import requests
import json
from dotenv import load_dotenv
import os
import log_config
from collections import OrderedDict
import re

logger = log_config.get_logger()


load_dotenv()
api_key = os.environ.get("API_KEY")
parameters = {}
crud_role_dataset = os.environ.get("ESTERM")

header = {"ekilex-api-key": api_key}
parameters = {"crudRoleDataset": crud_role_dataset}


def get_existing_source_id(source):
    logger.debug(f'Attempting to find ID for a source {source}')
    value_texts = [prop['valueText'] for prop in source['sourceProperties'] if prop['type'] == 'SOURCE_NAME']

    matching_sources = []

    for value_text in value_texts:
        # Normalise spaces because API normalises spaces when creating it
        value_text = re.sub(' +', ' ', value_text).strip()
        params = {"crudRoleDataset": crud_role_dataset}
        if '/' in value_text:
            value_text = value_text.replace('/', '?')
        endpoint = f"https://ekitest.tripledev.ee/ekilex/api/source/search/{value_text}"
        print(endpoint)
        response = requests.get(endpoint, headers=header, params=params)

        if response.status_code >= 200 and response.status_code < 300:
            try:
                response_data = response.json()
                for source_response in response_data:
                    if all(text in source_response['sourceNames'] for text in value_texts):
                        matching_sources.append(source_response)
            except (json.JSONDecodeError, IndexError):
                logger.warning(f"Failed to retrieve the ID of the source {value_texts[0]}. Response text: {response.text}")
        else:
            logger.warning(f"Received non-200 response when retrieving the ID of the source {value_texts[0]}. "
                           f"Status code: {response.status_code}, Response text: {response.text}")

    if matching_sources:
        # Sort by ID and select the one with the smallest ID
        matching_sources.sort(key=lambda x: x['id'])
        selected_source = matching_sources[0]
        logger.info(f'Selected source with smallest ID: {selected_source}')
        return selected_source['id']

    logger.warning(f'No matching source found for {source}.')
    return None


# Create a new source in Ekilex and return its ID
def create_source(source):
    logger.debug(f'Started creating source {source}')
    endpoint = "https://ekitest.tripledev.ee/ekilex/api/source/create"
    response = requests.post(endpoint, headers=header, params=parameters, json=source)

    if response.status_code >= 200 and response.status_code < 300:
        try:
            response_data = response.json()
            logger.info(f'Created source {source}. Response: {response_data}')
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
        logger.info(f'Source {existing_id} already exists')
        return existing_id, False
    #new_id = create_source(source)
    # Testing purposes
    new_id = 12345
    if new_id:
        logger.info(
            f"Created new source with ID {new_id} and name {source['sourceProperties'][0]['valueText']}.")
    return new_id, True


def assign_ids_to_all_sources(input_file):
    sources_with_ids_file = 'files/output/sources_with_ids.json'
    ids_of_created_sources_file = 'files/output/ids_of_created_sources.json'
    updated_sources = []
    ids_of_created_sources = []

    logger.info(f'Started assigning ID-s to all sources {sources_with_ids_file}')

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
    with open(sources_with_ids_file, 'w', encoding='utf-8') as source_files_with_ids:
        json.dump(updated_sources, source_files_with_ids, ensure_ascii=False, indent=4)

    logger.info('Created file with sources and their ID-s')

    # Create a file with list of ID-s of created sources
    with open(ids_of_created_sources_file, 'w', encoding='utf-8') as f:
        json.dump(ids_of_created_sources, f, ensure_ascii=False, indent=4)

    logger.info('Created file list of ID-s of created sources')

    return source_files_with_ids


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