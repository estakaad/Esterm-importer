import xml.etree.ElementTree as ET


#Find words and their languages of single concept
def extract_words(root):
  words = []
  for term in root.findall(".//languageGrp"):
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
  definitions = []
  for elem in root.findall(".//*[@type]"):
    if elem.attrib["type"] == "Definitsioon":
      definition_word = elem.text
      for elem in root.findall(".//*[@type]"):
        if elem.attrib["type"] == "et":
          definition = {"value": definition_word, "lang": "est", "definitionTypeCode": "definitsioon" }
          definitions.append(definition)
      return definitions


#Extract all concepts
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
