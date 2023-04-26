import requests
import log_config


logger = log_config.get_logger()

logger.handlers = []
logger.propagate = False

def save_term(concept, headers, parameters):

    try:
        res = requests.post(
            "https://ekitest.tripledev.ee/ekilex/api/term-meaning/save",
            params=parameters,
            json=concept,
            headers=headers, timeout=3)
        res.raise_for_status()
        logger.info("https://ekitest.tripledev.ee/ekilex/api/term-meaning/save - %s", concept)
    except requests.exceptions.HTTPError as errh:
        logger.exception("Http error {e}".format(e=errh))
    except requests.exceptions.ConnectionError as errc:
        logger.exception("Error connecting {e}".format(e=errc))
    except requests.exceptions.Timeout as errt:
        logger.exception("Timeout error {e}".format(e=errt))
    except requests.exceptions.RequestException as err:
        logger.exception("Unknown error {e}".format(e=e))

    return res
