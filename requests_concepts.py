import requests
import json
import os
from dotenv import load_dotenv
import log_config
from time import sleep

load_dotenv()

logger = log_config.get_logger()
logger.handlers = []
logger.propagate = False

def set_up_requests(dataset, environment):
    api_key = os.environ.get("API_KEY")
    crud_role_dataset = os.environ.get(dataset)

    header = {"ekilex-api-key": api_key}
    parameters = {"crudRoleDataset": crud_role_dataset}
    base_url = os.environ.get(environment)
    return parameters, header, base_url

session = requests.Session()

def import_concepts(file, dataset, saved_concepts_filename, not_saved_concepts_filename, environment):
    with open(file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    counter = 0
    concepts_saved = []
    concepts_not_saved = []

    for concept in data:

        try:
            concept_id = save_concept(concept, dataset, environment)

            if concept_id:
                concept['id'] = concept_id
                concepts_saved.append(concept)
                counter += 1
            else:
                concepts_not_saved.append(concept)
                logger.error("Response code was 200 but no ID received.")

        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError,
                requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
            concepts_not_saved.append(concept)
            logger.exception("Error: %s.", e)
            break

    with open(saved_concepts_filename, 'w', encoding='utf-8') as f:
        json.dump(concepts_saved, f, ensure_ascii=False, indent=4)

    with open(not_saved_concepts_filename, 'w', encoding='utf-8') as f:
        json.dump(concepts_not_saved, f, ensure_ascii=False, indent=4)


def save_concept(session, concept, dataset, environment):
    retries = 3
    timeout = 5
    parameters, header, base_url = set_up_requests(dataset, environment)

    while retries > 0:
        try:
            res = session.post(
                base_url + "/api/term-meaning/save",
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
                        base_url + "/api/term-meaning/save",
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


def update_word_ids(concepts_without_word_ids_file, dataset, concepts_dataset,
                    words_without_id_file, words_with_more_than_one_id_file, concepts_with_word_ids_file, environment):

    with open(concepts_without_word_ids_file, 'r', encoding='utf-8') as file:
        concepts = json.load(file)

    words_without_id = []
    words_with_more_than_one_id = []

    for concept in concepts:
        words = concept.get('words', [])
        for word in words:
            try:
                word_ids = get_word_id(word['valuePrese'], word['lang'], dataset, concepts_dataset, environment)
            except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
                logger.info(f"Connection timed out for {word['value']}. Moving on to the next word.")
                continue

            if word_ids:
                if len(word_ids) == 1:
                    word['wordId'] = word_ids[0]
                    logger.info(f'{word} with ID {word_ids[0]}')
                    word.pop('valuePrese', None)
                    word.pop('lang', None)
                elif len(word_ids) > 1:
                    words_with_more_than_one_id.append(word['valuePrese'])
                    logger.info(f'Word {word} has more than one lexemes in ÜS')
                else:
                    words_without_id.append(word['valuePrese'])
                    logger.info(f'Word {word} has does not have lexemes in ÜS (Case 1)')
            else:
                words_without_id.append(word['valuePrese'])
                logger.info(f'Word {word} has does not have lexemes in ÜS (Case 2)')

    with open(concepts_with_word_ids_file, 'w', encoding='utf-8') as file:
        json.dump(concepts, file, indent=4, ensure_ascii=False)

    with open(words_without_id_file, 'w', encoding='utf-8') as f:
        json.dump(words_without_id, f, ensure_ascii=False, indent=4)

    with open(words_with_more_than_one_id_file, 'w', encoding='utf-8') as f:
        json.dump(words_with_more_than_one_id, f, ensure_ascii=False, indent=4)


def get_word_id(session, word, lang, dataset, concepts_dataset, environment):
    parameters, header, base_url = set_up_requests(concepts_dataset, environment)

    try:
        res = session.get(
            f'{base_url}/api/word/ids/{word}/{dataset}/{lang}',
            params=parameters,
            headers=header,
            timeout=5
        )

        res.raise_for_status()
        return res.json()

    except requests.exceptions.RequestException as e:
        logger.error(f"Error in get_word_id for word: {word}, language: {lang}, dataset: {dataset}. Error: {e}")
        return None

    except ValueError:
        logger.error(f"Error decoding JSON for word: {word} in dataset: {dataset} for language: {lang}")
        return None
