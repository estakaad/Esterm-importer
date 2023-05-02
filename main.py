import os
import parse
import xml.etree.ElementTree as ET
import json
import api_requests
import os
from dotenv import load_dotenv
import xml_helpers

parser = ET.XMLParser(encoding="UTF-8")
tree = ET.parse("test.xml", parser=parser)
root = tree.getroot()
dataset_code = "estermtest"

load_dotenv()
api_key = os.environ.get("API_KEY")

header = {"ekilex-api-key": api_key}
parameters = {"crudRoleDataset": dataset_code}

#parse.extract_concepts(root, dataset_code, header, parameters)

xml_helpers.is_concept_aviation_related(root)