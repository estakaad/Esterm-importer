import requests


def save_term(term, headers, parameters):
    res = requests.post(
        "https://ekitest.tripledev.ee/ekilex/api/term-meaning/save",
        params=parameters,
        json=term,
        headers=headers)
    print(res)
    return res
