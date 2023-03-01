import requests
from dotenv.main import load_dotenv
import os


load_dotenv()
api_key=os.environ.get('API_KEY')

headers = {"ekilex-api-key": api_key}
parameters = {"crudRoleDataset": "mlt"}


def save_term(term, headers, parameters):
    res = requests.post("https://ekitest.tripledev.ee/ekilex/api/term-meaning/save",params=parameters,json=term,headers=headers)
    return res
