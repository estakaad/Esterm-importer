import xml.etree.ElementTree as ET
import json


tree = ET.parse("test.xml")
root = tree.getroot()

lang_name=""
concept = {}
datasetCode = "mlt"
words = []
definitions = []


#Find words and their languages
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


#Find definitions and their languages
for elem in root.findall(".//*[@type]"):
  if elem.attrib["type"] == "Definitsioon":
    definition_word = elem.text
    for elem in root.findall(".//*[@type]"):
      if elem.attrib["type"] == "et":
        definition = {"value": definition_word, "lang": "est", "definitionTypeCode": "definitsioon" }

    definitions.append(definition)
    print(definition)


concept = {
  "datasetCode": datasetCode,
  "definitions": definitions,
  "words": words
  }


print(concept)
