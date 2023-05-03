import xml.etree.ElementTree as ET
import json
import log_config
import xml_helpers
import api_requests

logger = log_config.get_logger()


def import_concepts(root, header, aviation_dataset, esterm_dataset):

    all_concepts = root.findall('.//conceptGrp')
    logger.info("Number of concept elements in XML: %s", len(all_concepts))

    esterm_concepts = []
    aviation_concepts = []
    sources = 0
    domains = 0

    for conceptGrp in root.findall("./conceptGrp"):

        logger.debug("Processing conceptGrp")

        if xml_helpers.concept_type(conceptGrp) == "concept":
            concept_dict = {}

            definition_list = []
            term_list = []

            for languageGrp in conceptGrp.findall("./languageGrp"):
                logger.debug("Processing languageGrp")

                definition_dict = {}

                for termGrp in languageGrp.findall("./termGrp"):
                    term_dict = {}
                    term_dict["value"] = termGrp.find("./term").text
                    term_dict["lang"] = xml_helpers.match_language(languageGrp.find("language").attrib["lang"])
                    term_list.append(term_dict)

                concept_dict["words"] = term_list

                for descripGrp in languageGrp.findall("./termGrp/descripGrp"):
                    descrip_type = descripGrp.find("descrip").attrib["type"]
                    if descrip_type == "Definitsioon":
                        descrip = descripGrp.find("descrip")
                        descrip_value = ET.tostring(descrip, encoding="unicode", method="text")
                        definition_dict["value"] = descrip_value
                        definition_dict["lang"] = xml_helpers.match_language(languageGrp.find("language").attrib["lang"])
                        definition_dict["definitionTypeCode"] = "definitsioon"

                if definition_dict:
                    definition_list.append(definition_dict)

            if xml_helpers.is_concept_aviation_related(conceptGrp):
                concept_dict["datasetCode"] = aviation_dataset
            else:
                concept_dict["datasetCode"] = esterm_dataset

            if definition_list:
                concept_dict["definitions"] = definition_list

            logger.info("Added dataset code: %s", concept_dict["datasetCode"])
            logger.info("Added definitions: %s", definition_list)
            logger.info("Added words: %s", term_list)

            if concept_dict["datasetCode"] == aviation_dataset:
                aviation_concepts.append(concept_dict)
            else:
                esterm_concepts.append(concept_dict)

            parameters = {"crudRoleDataset": concept_dict["datasetCode"]}
            api_requests.save_term(concept_dict, header, parameters)

        if xml_helpers.concept_type(conceptGrp) == "source":
            logger.info("This concept element is a source, not a concept.")
            sources += 1
        if xml_helpers.concept_type(conceptGrp) == "domain":
            logger.info("This concept element is a domain, not a concept.")
            domains += 1

        logger.info("Number of Esterm concepts parsed: %s", len(esterm_concepts))
        logger.info("Number of aviation concepts parsed: %s", len(aviation_concepts))
        logger.info("Number of sources parsed: %s", str(sources))
        logger.info("Number of domains parsed: %s", str(domains))

        if len(esterm_concepts) + len(aviation_concepts) + sources + domains == len(all_concepts):
            logger.info("Number of elements parsed is equal to total number of concept elements.")
        else:
            logger.info("Number of elements parsed is not equal to total number (%s) of concept elements.",
                str(len(all_concepts)))

    return True
