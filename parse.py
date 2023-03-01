import xml.etree.ElementTree as ET
import json


#Find words and their languages of single concept
def extract_words(root):
  for term in root.findall(".//languageGrp"):
    #Returns list of words with values and languages
    for lang in term.findall(".//language"):
      if lang.attrib["type"] == "fr":
        lang_name="fra"
      if lang.attrib["type"] == "en":
        lang_name="eng"
      if lang.attrib["type"] == "et":
        lang_name="est"

    for term in term.findall(".//term"):
      word = {"value": term.text, "lang": lang_name}
      words.append(word)
  return words


#Find definitions and their languages of single concept
def extract_definitions(root):
  for elem in root.findall(".//*[@type]"):
    if elem.attrib["type"] == "Definitsioon":
      definition_word = elem.text
      for elem in root.findall(".//*[@type]"):
        if elem.attrib["type"] == "et":
          definition = {"value": definition_word, "lang": "est", "definitionTypeCode": "definitsioon" }
      definitions.append(definition)
      return definitions


#Create dictionary which contains a list of definitions and a list of words
def create_concept(dataset_code, definitions, words):
  concept = {
    "datasetCode": dataset_code,
    "definitions": definitions,
    "words": words
    }
  return concept


tree = ET.parse("test.xml")
root = tree.getroot()

concept = {}
dataset_code = "mlt"
words = []
definitions = []


words = extract_words(root)
definitions = extract_definitions(root)

concept = create_concept(dataset_code, definitions, words)

print(concept)
