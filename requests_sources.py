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

header = {"ekilex-api-key": api_key}

def get_existing_source_id(source):
    try:

        logger.debug(f'Attempting to find ID for a source {source}')

        value_texts = [prop['valueText'] for prop in source['sourceProperties'] if prop['type'] == 'SOURCE_NAME']
        # Normalise source names or matching will give unexpected results
        value_texts = [re.sub(' +', ' ', value_text).strip() for value_text in value_texts]

        value_for_request = value_texts[0].replace('/', '*')

        #endpoint = f"https://ekitest.tripledev.ee/ekilex/api/source/search/{value_for_request}"
        endpoint = f"https://ekilex.ee/api/source/search/{value_for_request}"

        response = requests.get(endpoint, headers=header)

        if response.status_code >= 200 and response.status_code < 300:
            response_data = response.json()
            if response_data:
                for item in response_data:
                    source_names_in_response = []
                    for prop in item['sourceProperties']:
                        if prop['type'] == 'SOURCE_NAME':
                            source_names_in_response.append(prop['valueText'])

                    if set(source_names_in_response) == set(value_texts):
                        logger.info(f'There was a response and it contained a source with the same names. ID: {item["id"]}')
                        return item['id']

                logger.info('No match found in any of the objects in the response.')
                return None
            else:
                logger.info(f'The response was 200, but it was empty. The source name was: {value_for_request}')
                return None
    except Exception as e:
        logger.error(f'An error occurred getting the ID of source {source}: {e}')
        return None
    return None


# Create a new source in Ekilex and return its ID
def create_source(source):
    logger.debug(f'Started creating source {source}')
    #endpoint = "https://ekitest.tripledev.ee/ekilex/api/source/create"
    endpoint = "https://ekilex.ee/api/source/create"
    response = requests.post(endpoint, headers=header, json=source)

    if response.status_code >= 200 and response.status_code < 300:
        try:
            response_data = response.json()
            logger.info(f'Created source {source}. Response: {response_data}')
            return response_data['id']
        except json.JSONDecodeError:
            logger.warning(source)
            logger.warning(f"Failed to parse JSON from response when creating source Response text: {response.text}")

    else:
        logger.warning(source)
        logger.warning(f"Received non-200 response when creating source. "
                       f"Status code: {response.status_code}, Response text: {response.text}")
    return None

def assign_ids_to_expert_sources(
        expert_sources_without_ids_filename, expert_sources_with_ids_filename, ids_of_created_sources_file):

    updated_sources = []
    ids_of_created_expert_sources = []

    logger.info(f'Started assigning ID-s to all expert sources {expert_sources_without_ids_filename}')

    with open(expert_sources_without_ids_filename, 'r', encoding='utf-8') as f:
        data = json.load(f)

        for source in data:
            source_id = create_source(source)
            if source_id:
                logger.info(f'Created expert source with ID {source_id}')
                source['id'] = source_id
                updated_sources.append(source)
                ids_of_created_expert_sources.append(source_id)

    with open(expert_sources_with_ids_filename, 'w', encoding='utf-8') as f:
        json.dump(updated_sources, f, ensure_ascii=False, indent=4)

    with open(ids_of_created_sources_file, 'w', encoding='utf-8') as f:
        json.dump(ids_of_created_expert_sources, f, ensure_ascii=False, indent=4)

    logger.info(f'Number of created sources: {len(ids_of_created_expert_sources)}')
    return expert_sources_with_ids_filename


# Try getting existing source's ID, if source doesn't exist, create a new one and return its ID.
# If source already existed, return False. If source was created, return True.
def get_or_create_source(source):
    existing_id = get_existing_source_id(source)
    if existing_id:
        logger.info(f'Source {existing_id} already exists')
        return existing_id, False
    logger.info(f'Cannot find existing source, should create a new one.')
    new_id = create_source(source)
    if new_id:
        logger.info(
            f"Created new source with ID {new_id} and name {source['sourceProperties'][0]['valueText']}.")
    return new_id, True


def assign_ids_to_all_sources(input_file, sources_with_ids_filename, ids_of_created_sources_filename):

    updated_sources = []
    ids_of_created_sources = []

    logger.info(f'Started assigning ID-s to all sources {input_file}')

    with open(input_file, 'r', encoding='utf-8') as f:
        count_existing_sources = 0
        count_created_sources = 0
        data = json.load(f)

        for source in data:
            source_id, was_created = get_or_create_source(source)
            if source_id:
                ordered_source = OrderedDict([('id', source_id)] + list(source.items()))
                updated_sources.append(ordered_source)
                if was_created:
                    ids_of_created_sources.append(source_id)
                    count_created_sources += 1
                else:
                    count_existing_sources += 1

    # Create a file with sources and their ID-s
    with open(sources_with_ids_filename, 'w', encoding='utf-8') as source_files_with_ids:
        json.dump(updated_sources, source_files_with_ids, ensure_ascii=False, indent=4)

    logger.info('Created file with sources and their ID-s')

    # Create a file with list of ID-s of created sources
    with open(ids_of_created_sources_filename, 'w', encoding='utf-8') as f:
        json.dump(ids_of_created_sources, f, ensure_ascii=False, indent=4)

    logger.info('Created file list of ID-s of created sources')
    logger.info('Number of existing sources: ' + str(count_existing_sources))
    logger.info('Number of created sources: ' + str(count_created_sources))
    return source_files_with_ids


def delete_created_sources(file):
    with open(file, 'r', encoding='utf-8') as file:
        source_ids = json.load(file)

    #endpoint = "https://ekitest.tripledev.ee/ekilex/api/source/delete"
    endpoint = "https://ekilex.ee/api/source/delete"

    for source_id in source_ids:
        params = {
            'sourceId': source_id,
        }

        response = requests.delete(endpoint, headers=header)

        if response.status_code >= 200 and response.status_code < 300:
            logger.info(f"Successfully deleted source with ID {source_id}.")
        else:
            logger.info(f"Failed to delete source with ID {source_id}. Status code: {response.status_code}, "
                        f"Response text: {response.text}")