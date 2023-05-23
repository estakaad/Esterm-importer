import os
import parse
import xml.etree.ElementTree as ET
import json
import api_requests
import os
from dotenv import load_dotenv
import xml_helpers

# parser = ET.XMLParser(encoding="UTF-8")
# tree = ET.parse("test.xml", parser=parser)
# root = tree.getroot()

json_output = 'output.json'

load_dotenv()
api_key = os.environ.get("API_KEY")
parameters = {}
crud_role_dataset = os.environ.get("KALANDUS")

header = {"ekilex-api-key": api_key}
parameters = {"crudRoleDataset": crud_role_dataset}

api_requests.save_term(json_output, header, parameters)