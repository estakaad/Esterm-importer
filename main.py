import os
import parse
import xml.etree.ElementTree as ET
import json
import api_requests
from dotenv.main import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s :: %(levelname)s :: %(message)s', filename="import")

tree = ET.parse("test.xml")
root = tree.getroot()

dataset_code = "mlt"

concepts = parse.extract_concepts(root, "mlt")

load_dotenv()
api_key=os.environ.get('API_KEY')

headers = {"ekilex-api-key": api_key}
parameters = {"crudRoleDataset": "mlt"}

for concept in concepts:
    api_requests.save_term(concept, headers, parameters)
