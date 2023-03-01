import os
import parse
import xml.etree.ElementTree as ET
import json

tree = ET.parse("esterm_pubKuup.xml")
root = tree.getroot()

concept = {}
dataset_code = "mlt"

concepts = parse.extract_concepts(root, "mlt")

print(json.dumps(concepts, indent=2))





