import xml.etree.ElementTree as ET
import json
import log_config
import xml_helpers
import api_requests

logger = log_config.get_logger()


def import_concepts(root, header):

    all_concepts = root.findall('.//conceptGrp')
    logger.info("Number of concept elements in XML: %s", len(all_concepts))

    esterm_concepts = []
    aviation_concepts = []
    sources = 0

    # Loop through each <conceptGrp> element
    for conceptGrp in root.findall("./conceptGrp"):

        logger.debug("Processing conceptGrp")

        if xml_helpers.is_element_source(conceptGrp):
            sources += 1
        else:
            # Create a dictionary for the concept
            concept_dict = {}

            # The concept consists of a list of definitions and a list of terms (words)
            definition_list = []
            term_list = []

            # Loop through each <languageGrp> element
            for languageGrp in conceptGrp.findall("./languageGrp"):
                logger.debug("Processing languageGrp")

                # Create a dictionary for the definition
                definition_dict = {}

                for termGrp in languageGrp.findall("./termGrp"):
                    term_dict = {}

                    # Get the value of the <term> element and
                    # add it to the dictionary for the term
                    term_dict["value"] = termGrp.find("./term").text
                    # Get the value of the <language> element and
                    # add it to the dictionary for the term
                    term_dict["lang"] = xml_helpers.match_language(languageGrp.find("language").attrib["lang"])
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
                        definition_dict["lang"] = xml_helpers.match_language(languageGrp.find("language").attrib["lang"])
                        definition_dict["definitionTypeCode"] = "definitsioon"

                # Add the definition dictionary to the list of definitions
                if definition_dict:
                    definition_list.append(definition_dict)

            if xml_helpers.is_concept_aviation_related(conceptGrp):
                # Add datasetCode to the concept dictionary
                concept_dict["datasetCode"] = "avi"
            else:
                concept_dict["datasetCode"] = "estt"

            # Add the list of definitions to the concept dictionary
            if definition_list:
                concept_dict["definitions"] = definition_list

            logger.info("Added dataset code: %s", concept_dict["datasetCode"])
            logger.info("Added definitions: %s", definition_list)
            logger.info("Added words: %s", term_list)

            if concept_dict["datasetCode"] == "avi":
                # Add the concept dictionary to the output list
                aviation_concepts.append(concept_dict)
            else:
                esterm_concepts.append(concept_dict)

            logger.info("Number of Esterm concepts parsed: %s", len(esterm_concepts))
            logger.info("Number of aviation concepts parsed: %s", len(aviation_concepts))
            logger.info("Number of sources parsed: %s", str(sources))

            if len(esterm_concepts) + len(aviation_concepts) + sources == len(all_concepts):
                logger.info("Number of elements parsed is equal to total number of concept elements.")
            else:
                logger.info("Number of elements parsed is not equal to total number (%s) of concept elements.", str(len(all_concepts)))

            parameters = {"crudRoleDataset": concept_dict["datasetCode"]}

            #api_requests.save_term(concept_dict, header, parameters)

    return True
