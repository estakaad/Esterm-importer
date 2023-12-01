import requests
import json
import os
from dotenv import load_dotenv
import log_config
from datetime import datetime
import copy
from time import sleep


logger = log_config.get_logger()

logger.handlers = []
logger.propagate = False


def set_up_requests(dataset):
    load_dotenv()
    api_key = os.environ.get("API_KEY")
    if 'est' in dataset:
        crud_role_dataset = os.environ.get("ESTERM")
    elif 'avi' in dataset:
        crud_role_dataset = os.environ.get("AVI")
    else:
        print(dataset)

    header = {"ekilex-api-key": api_key}
    parameters = {"crudRoleDataset": crud_role_dataset}
    return parameters, header


def import_concepts(file, dataset, max_objects=5000000):
    with open(file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    counter = 0
    concepts_saved = []
    concepts_not_saved = []

    for concept in data:
        concept_copy = copy.copy(concept)

        if max_objects is not None and counter >= max_objects:
            break

        # Remove empty 'notes' entries
        if 'notes' in concept_copy:
            concept_copy['notes'] = [note for note in concept_copy['notes'] if note != [] and note != {}]

        try:
            concept_id = save_concept(concept_copy, dataset)

            if concept_id:
                concept_copy['id'] = concept_id
                concepts_saved.append(concept_copy)
                counter += 1
            else:
                concepts_not_saved.append(concept_copy)
                logger.error("Response code was 200 but no ID received.")

        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError,
                requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
            concepts_not_saved.append(concept)
            logger.exception("Error: %s.", e)
            break

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    saved_filename = f'files/import/esterm-01-12-23/{timestamp}_concepts_saved.json'
    not_saved_filename = f'files/import/esterm-01-12-23/{timestamp}_concepts_not_saved.json'

    with open(saved_filename, 'w', encoding='utf-8') as f:
        json.dump(concepts_saved, f, ensure_ascii=False, indent=4)

    with open(not_saved_filename, 'w', encoding='utf-8') as f:
        json.dump(concepts_not_saved, f, ensure_ascii=False, indent=4)


def save_concept(concept, dataset):
    retries = 3
    timeout = 5

    parameters, header = set_up_requests(dataset)

    while retries > 0:
        try:
            res = requests.post(
                "https://ekitest.tripledev.ee/ekilex/api/term-meaning/save",
                params=parameters,
                json=concept,
                headers=header,
                timeout=timeout
            )

            if res.status_code != 200:
                raise requests.exceptions.HTTPError(f"Received {res.status_code} status code.")

            response_json = res.json()
            concept_id = response_json.get('id')

            logger.info("URL: %s - Concept: %s - Status Code: %s - Concept ID: %s",
                        "https://ekitest.tripledev.ee/ekilex/api/term-meaning/save",
                        concept,
                        res.status_code,
                        concept_id)

            return concept_id

        except (requests.exceptions.ReadTimeout, requests.exceptions.HTTPError):
            retries -= 1
            if retries > 0:
                sleep(2)

    logger.error("Failed to save concept after maximum retries.")
    return None


def update_word_ids(filename, dataset, concepts_dataset):
    with open(filename, 'r', encoding='utf-8') as file:
        concepts = json.load(file)

    words_without_id = []
    words_with_more_than_one_id = []

    for concept in concepts:
        words = concept.get('words', [])
        for word in words:
            #print(word['value'])
            try:
                word_ids = get_word_id(word['value'], word['lang'], dataset, concepts_dataset)
            except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
                logger.info(f"Connection timed out for {word['value']}. Moving on to the next word.")
                continue

            if word_ids:
                if len(word_ids) == 1:
                    word['wordId'] = word_ids[0]
                    logger.info(f'{word} with ID {word_ids[0]}')
                elif len(word_ids) > 1:
                    words_with_more_than_one_id.append(word['value'])
                    logger.info(f'Word {word} has more than one lexemes in ÜS')
                else:
                    words_without_id.append(word['value'])
                    logger.info(f'Word {word} has does not have lexemes in ÜS (Case 1)')
            else:
                words_without_id.append(word['value'])
                logger.info(f'Word {word} has does not have lexemes in ÜS (Case 2)')

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    words_without_id_file = f'files/import/esterm-01-12-23/{timestamp}_words_without_id1.json'
    words_with_more_than_one_id_file = f'files/import/esterm-01-12-23/{timestamp}_words_with_more_than_one_id1.json'


    with open(f'files/import/esterm-01-12-23/concepts_with_word_ids1.json', 'w', encoding='utf-8') as file:
        json.dump(concepts, file, indent=4, ensure_ascii=False)

    with open(words_without_id_file, 'w', encoding='utf-8') as f:
        json.dump(words_without_id, f, ensure_ascii=False, indent=4)

    with open(words_with_more_than_one_id_file, 'w', encoding='utf-8') as f:
        json.dump(words_with_more_than_one_id, f, ensure_ascii=False, indent=4)




def get_word_id(word, lang, dataset, concepts_dataset):
    parameters, header = set_up_requests(concepts_dataset)

    res = requests.get(
        f'https://ekitest.tripledev.ee/ekilex/api/word/ids/{word}/{dataset}/{lang}',
        params=parameters,
        headers=header, timeout=5)

    if res.status_code == 200:
        try:
            response = res.json()
            return response
        except ValueError:
            print(f"Error decoding JSON for word: {word} in dataset: {dataset} for language: {lang}")
            return None
    else:
        return None