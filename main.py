import os
import parse
import xml.etree.ElementTree as ET
import json
import api_requests
import os
from dotenv import load_dotenv
#import logging


#logging.basicConfig(level=logging.INFO, format='%(asctime)s :: %(levelname)s :: %(message)s', filename="import")

parser = ET.XMLParser(encoding="UTF-8")
tree = ET.parse("test.xml", parser=parser)
root = tree.getroot()
dataset_code = "mlt"

concepts = parse.extract_concepts(root, dataset_code)

load_dotenv()
api_key = os.environ.get("API_KEY")

headers = {"ekilex-api-key": api_key}
parameters = {"crudRoleDataset": "mlt"}

for concept in concepts:
    api_requests.save_term(concept, headers, parameters)