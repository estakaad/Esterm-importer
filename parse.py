import xml.etree.ElementTree as ET
import json
import logging

# Configure the logging module
logging.basicConfig(
    filename="import_log.log",
    filemode="w",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.DEBUG
)


# Find term"s or definition"s languages and match it with
# the language abbreviation used in API
def match_language(lang):
    if lang == "FR":
        lang_name = "fra"
    if lang == "EN-GB":
        lang_name = "eng"
    if lang == "ET":
        lang_name = "est"
    if lang == "FI":
        lang_name = "fin"
    if lang == "RU":
        lang_name = "rus"
    if lang == "XO":
        lang_name = "xho"
    # Actually no idea what language is XH
    if lang == "XH":
        lang_name = "xho"
    if lang == "DE":
        lang_name = "deu"
    return lang_name


def extract_concepts(root, dataset_code):

    all_concepts = root.findall('.//conceptGrp')
    logging.info("Number of concepts: %s", len(all_concepts))

    concepts = []

    # Loop through each <conceptGrp> element
    for conceptGrp in root.findall("./conceptGrp"):

        logging.debug("Processing conceptGrp")

        # Create a dictionary for the concept
        concept_dict = {}

        # The concept consists of a list of definitions and a list of terms (words)
        definition_list = []
        term_list = []

        # Loop through each <languageGrp> element
        for languageGrp in conceptGrp.findall("./languageGrp"):
            logging.debug("Processing languageGrp")

            # Create a dictionary for the definition
            definition_dict = {}

            for termGrp in languageGrp.findall("./termGrp"):
                term_dict = {}

                # Get the value of the <term> element and
                # add it to the dictionary for the term
                term_dict["value"] = termGrp.find("./term").text
                # Get the value of the <language> element and
                # add it to the dictionary for the term
                term_dict["lang"] = match_language(languageGrp.find("language").attrib["lang"])
                print(term_dict)
                # Add the term dictionary to the list of terms
                term_list.append(term_dict)

            concept_dict["words"] = term_list

            # Loop through each <descripGrp> element and
            # add each <descrip> element to the dictionary
            for descripGrp in languageGrp.findall("./termGrp/descripGrp"):
                descrip_type = descripGrp.find("descrip").attrib["type"]
                if descrip_type == "Definitsioon":
                    descrip = descripGrp.find("descrip")
                    descrip_value = ET.tostring(descrip, encoding="unicode", method="text")
                    definition_dict["value"] = descrip_value
                    definition_dict["lang"] = match_language(languageGrp.find("language").attrib["lang"])
                    definition_dict["definitionTypeCode"] = "definitsioon"

            # Add the definition dictionary to the list of definitions
            if definition_dict:
                definition_list.append(definition_dict)

        # Add datasetCode to the concept dictionary
        concept_dict["datasetCode"] = dataset_code

        # Add the list of definitions to the concept dictionary
        if definition_list:
            concept_dict["definitions"] = definition_list

        logging.info("Added definitions: %s", definition_list)
        logging.info("Added words: %s", term_list)

        # Add the concept dictionary to the output list
        concepts.append(concept_dict)

        logging.debug("Number of concepts parsed: %s", len(concepts))

    return concepts


# Return list of all unique languages present in XML
def find_all_languages(root):
    all_languages = []
    for term in root.findall(".//languageGrp"):
        for lang in term.findall(".//language"):
            all_languages.append(lang.attrib["lang"])

    set_res = set(all_languages)
    unique_languages = (list(set_res))

    return unique_languages
