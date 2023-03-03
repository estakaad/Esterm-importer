import os
import parse
import xml.etree.ElementTree as ET
import json
import api_requests
from dotenv.main import load_dotenv


tree = ET.parse("esterm_pubKuup.xml")
root = tree.getroot()

dataset_code = "mlt"

concepts = parse.extract_concepts(root, "mlt")

load_dotenv()
api_key=os.environ.get('API_KEY')

headers = {"ekilex-api-key": api_key}
parameters = {"crudRoleDataset": "mlt"}

for concept in concepts:
    #print(concept)
    api_requests.save_term(concept, headers, parameters)
