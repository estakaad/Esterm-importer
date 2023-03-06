import xml.etree.ElementTree as ET
import re
import json


#Find term's or definition's languages and match it with
#the language abbreviation used in API
def match_language(lang):
  if lang.attrib["lang"] == "FR":
    lang_name="fra"
  if lang.attrib["lang"] == "EN-GB":
    lang_name="eng"
  if lang.attrib["lang"] == "ET":
    lang_name="est"
  if lang.attrib["lang"] == "FI":
    lang_name="fin"
  if lang.attrib["lang"] == "RU":
    lang_name="rus"
  if lang.attrib["lang"] == "XO":
    lang_name="xho"
  #Actually no idea what language is XH
  if lang.attrib["lang"] == "XH":
    lang_name="xho"
  if lang.attrib["lang"] == "DE":
    lang_name="deu"

  return lang_name


#Return list of words and the languages they're in (for one concept)
def extract_words(root):
  words = []
  for term in root.findall(".//languageGrp"):

    for lang in term.findall(".//language"):
      lang_name = match_language(lang)

    for term in term.findall(".//term"):
      word = {"value": term.text, "lang": lang_name}
      words.append(word)

  return words


#Return list of definitions and the languages they're in (for one concept)
def extract_definitions(root):
  definitions = []
  for term in root.findall(".//languageGrp"):
    for lang in term.findall(".//language"):
      lang_name = match_language(lang)

    for elem in term.findall(".//*[@type]"):
      if elem.attrib["type"] == "Definitsioon":
        definition_word = ET.tostring(elem, encoding='utf8', method='xml')
        definition_word = json.dumps(definition_word.decode("utf-8"))
        definition = {"value": definition_word, "lang": lang_name, "definitionTypeCode": "definitsioon" }
        definitions.append(definition)

    return definitions


#Combine words and definitions to return the list of all concepts
def extract_concepts(root, dataset_code):
  concepts = []
  for concept in root.findall("./conceptGrp"):
    words = extract_words(concept)
    definitions = extract_definitions(concept)
    concept = {
      "datasetCode": dataset_code,
      "definitions": definitions,
      "words": words
      }
    concepts.append(concept)

  return concepts


#Return list of all unique languages present in XML
def find_all_languages(root):
  all_languages = []
  for term in root.findall(".//languageGrp"):
    for lang in term.findall(".//language"):
      all_languages.append(lang.attrib["lang"])

  set_res = set(all_languages)
  unique_languages = (list(set_res))

  return unique_languages
