import requests
import json
import log_config
from pathlib import Path

logger = log_config.get_logger()

logger.handlers = []
logger.propagate = False

def save_term(json_file_path, header, parameters, max_objects=None):
    script_dir = Path(__file__).resolve().parent

    with open(script_dir / json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    counter = 0

    for concept in data:
        try:
            if max_objects is not None and counter >= max_objects:
                break

            res = requests.post(
                "https://ekitest.tripledev.ee/ekilex/api/term-meaning/save",
                params=parameters,
                json=concept,
                headers=header, timeout=3)
            res.raise_for_status()
            logger.info("https://ekitest.tripledev.ee/ekilex/api/term-meaning/save - %s - %s", concept, res)

            counter += 1

        except requests.exceptions.HTTPError as errh:
            logger.exception("Http error {e}".format(e=errh))
        except requests.exceptions.ConnectionError as errc:
            logger.exception("Error connecting {e}".format(e=errc))
        except requests.exceptions.Timeout as errt:
            logger.exception("Timeout error {e}".format(e=errt))
        except requests.exceptions.RequestException as err:
            logger.exception("Unknown error {e}".format(e=err))

    return res
