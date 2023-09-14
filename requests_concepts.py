import requests
import json
import os
from dotenv import load_dotenv
import log_config
from datetime import datetime


logger = log_config.get_logger()

logger.handlers = []
logger.propagate = False


def set_up_requests():
    load_dotenv()
    api_key = os.environ.get("API_KEY")
    crud_role_dataset = os.environ.get("AVI")

    header = {"ekilex-api-key": api_key}
    parameters = {"crudRoleDataset": crud_role_dataset}

    return parameters, header


def import_concepts(file, max_objects=5):
    with open(file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    counter = 0
    concepts_saved = []
    concepts_not_saved = []

    for concept in data:
        if max_objects is not None and counter >= max_objects:
            break

        try:
            concept_id = save_concept(concept)

            if concept_id:
                transformed_concept = concept
                transformed_concept['id'] = concept_id
                concepts_saved.append(transformed_concept)
                counter += 1

            else:
                concepts_not_saved.append(concept)
                remaining = max_objects - counter - 1

                concepts_not_saved.extend(data[counter+1:counter+1+remaining])
                logger.error("Response code was 200 but no ID received. Stopping processing.")
                break

        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError,
                requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
            concepts_not_saved.append(concept)

            remaining = max_objects - counter - 1
            concepts_not_saved.extend(data[counter+1:counter+1+remaining])
            logger.exception("Error: %s. Stopping processing.", e)
            break

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    saved_filename = f'files/import/{timestamp}_concepts_saved.json'
    not_saved_filename = f'files/import/{timestamp}_concepts_not_saved.json'

    with open(saved_filename, 'w', encoding='utf-8') as f:
        json.dump(concepts_saved, f, ensure_ascii=False, indent=4)

    with open(not_saved_filename, 'w', encoding='utf-8') as f:
        json.dump(concepts_not_saved, f, ensure_ascii=False, indent=4)


def save_concept(concept):
    parameters, header = set_up_requests()

    res = requests.post(
        "https://ekitest.tripledev.ee/ekilex/api/term-meaning/save",
        params=parameters,
        json=concept,
        headers=header, timeout=3)

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


def update_word_ids(filename, dataset):
    with open(filename, 'r', encoding='utf-8') as file:
        concepts = json.load(file)

    words_without_id = []
    words_with_more_than_one_id = []

    for concept in concepts:
        words = concept.get('words', [])
        for word in words:

            word_ids = get_word_id(word['value'], word['lang'], dataset)
            print(f"IDs for {word['value']}: {word_ids}")

            if len(word_ids) == 1:
                word['wordId'] = word_ids
            elif len(word_ids) > 1:
                words_with_more_than_one_id.append(word)
            else:
                words_without_id.append(word)

    print("Words without ID:", words_without_id)
    print("Words with more than one ID:", words_with_more_than_one_id)

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    words_without_id_file = f'files/import/{timestamp}_words_without_id.json'
    words_with_more_than_one_id_file = f'files/import/{timestamp}_words_with_more_than_one_id.json'

    with open(words_without_id_file, 'w', encoding='utf-8') as f:
        json.dump(words_without_id, f, ensure_ascii=False, indent=4)

    with open(words_with_more_than_one_id_file, 'w', encoding='utf-8') as f:
        json.dump(words_with_more_than_one_id, f, ensure_ascii=False, indent=4)

    with open('files/import/concepts_with_word_ids.json', 'w', encoding='utf-8') as file:
        json.dump(concepts, file, indent=4, ensure_ascii=False)



def get_word_id(word, lang, dataset):
    parameters, header = set_up_requests()

    res = requests.get(
        f'https://ekitest.tripledev.ee/ekilex/api/word/ids/{word}/{dataset}/{lang}',
        params=parameters,
        headers=header, timeout=3)

    if res.status_code == 200:
        response = res.json()
        return response
    else:
        return None