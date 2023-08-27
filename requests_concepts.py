import requests
import json
from dotenv import load_dotenv
import log_config
import os


logger = log_config.get_logger()

logger.handlers = []
logger.propagate = False

def set_up_requests():
    load_dotenv()
    api_key = os.environ.get("API_KEY")
    crud_role_dataset = os.environ.get("ESTERM")

    header = {"ekilex-api-key": api_key}
    parameters = {"crudRoleDataset": crud_role_dataset}

    return parameters, header


def import_concepts(file, max_objects=None):

    with open(file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    counter = 0

    list_of_concepts_saved = []

    for concept in data:
        try:
            if max_objects is not None and counter >= max_objects:
                break

            concept_id = save_concept(concept)
            list_of_concepts_saved.append(concept_id)

            counter += 1

        except requests.exceptions.HTTPError as errh:
            logger.exception("Http error {e}".format(e=errh))
        except requests.exceptions.ConnectionError as errc:
            logger.exception("Error connecting {e}".format(e=errc))
        except requests.exceptions.Timeout as errt:
            logger.exception("Timeout error {e}".format(e=errt))
        except requests.exceptions.RequestException as err:
            logger.exception("Unknown error {e}".format(e=err))

    with open('files/output/list_of_concepts_saved.json', 'w', encoding='utf-8') as f:
        json.dump(list_of_concepts_saved, f)


def save_concept(concept):

    parameters, header = set_up_requests()

    res = requests.post(
        "https://ekitest.tripledev.ee/ekilex/api/term-meaning/save",
        params=parameters,
        json=concept,
        headers=header, timeout=3)
    res.raise_for_status()

    response_json = res.json()
    concept_id = response_json.get('id')

    logger.info("URL: %s - Concept: %s - Status Code: %s - Concept ID: %s",
                "https://ekitest.tripledev.ee/ekilex/api/term-meaning/save",
                concept,
                res.status_code,
                concept_id)

    return concept_id