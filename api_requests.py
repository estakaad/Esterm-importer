import requests
import logging


def save_term(term, headers, parameters):

    try:
        res = requests.post(
            "https://ekitest.tripledev.ee/ekilex/api/term-meaning/save",
            params=parameters,
            json=term,
            headers=headers, timeout=3)
        res.raise_for_status()
    except requests.exceptions.HTTPError as errh:
        logging.exception("Http error {e}".format(e=errh))
    except requests.exceptions.ConnectionError as errc:
        logging.exception("Error connecting {e}".format(e=errc))
    except requests.exceptions.Timeout as errt:
        logging.exception("Timeout error {e}".format(e=errt))
    except requests.exceptions.RequestException as err:
        logging.exception("Unknnown error {e}".format(e=e))

    return res
