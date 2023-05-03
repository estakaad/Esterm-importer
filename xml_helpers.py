import xml.etree.ElementTree as ET
import log_config


logger = log_config.get_logger()

logger.handlers = []
logger.propagate = False


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


# Return list of all unique languages present in XML
def find_all_languages(root):
    all_languages = []
    for term in root.findall(".//languageGrp"):
        for lang in term.findall(".//language"):
            all_languages.append(lang.attrib["lang"])

    set_res = set(all_languages)
    unique_languages = (list(set_res))

    return unique_languages


def find_all_description_types(root):
    all_description_types = []
    for term in root.findall(".//descripGrp"):
        for description_type in term.findall(".//descrip"):
            all_description_types.append(description_type.attrib["type"])

    set_res = set(all_description_types)
    unique_description_types = (list(set_res))

    return unique_description_types

def find_all_transaction_types(root):
    all_transacGrp_types = []
    for term in root.findall(".//transacGrp"):
        for transaction_type in term.findall(".//transac"):
            all_transacGrp_types.append(transaction_type.attrib["type"])

    set_res = set(all_transacGrp_types)
    unique_transaction_types = (list(set_res))

    return unique_transaction_types

# Return True, if the concept is an aviation concept.
def is_concept_aviation_related(concept):
    sub_categories_list = ['Aeronavigatsioonilised kaardid', 'Lennukõlblikkus', 'Lennuliikluse korraldamine',
                      'Lennumeteoroloogia', 'Lennunduse (rahvusvaheline) reguleerimine', 'Lennundusjulgestus',
                      'Lennundusohutus', 'Lennundusside (telekommunikatsioon)',
                      'Lennundusspetsialistid, nende load ja pädevused', 'Lennundusspetsialistide koolitus',
                      'Lennundusspetsialistide tervisekontroll', 'Lennundusteave', 'Lennureeglid', 'Lennutegevus',
                      'Lennuväljad ja kopteriväljakud', 'Lennuõnnetused ja –intsidendid',
                      'Ohtlike ainete/kaupade õhuvedu', 'Otsing ja päästmine',
                      'Protseduuride lihtsustamine lennunduses', 'Reisijatevedu ja –teenindamine', 'Õhusõidukid',
                      'Õhusõidukite keskkonnakõlblikkus (müra, emissioonid)',
                      'Õhusõidukite riikkondsus ja registreerimistunnused']

    # Check whether "Valdkonnaviide" contains value "TR8" (Lenoch classificator for aero transport)
    domain_references = concept.findall(".//descrip[@type='Valdkonnaviide']")

    for i in domain_references:
        if "TR8" in ET.tostring(i, encoding="unicode", method="text"):
            logger.debug("This is aviation concept, because \"Valdkonnaviide\" contains \"TR8\"")
            return True
        else:
            logger.debug("This is not aviation concept, because \"Valdkonnaviide\" does not contain \"TR8\"")

    # Check whether "Alamvaldkond_" contains value which is present in the list of aviation sub categories
    sub_categories = concept.findall(".//descrip[@type='Alamvaldkond_']")

    for s in sub_categories:
        sub_category = ET.tostring(s, encoding="unicode", method="text").strip()
        if sub_category in sub_categories_list:
            logger.debug("This is aviation concept, because %s is a relevant sub category.", sub_category)
            return True
        else:
            logger.debug("This is not aviation concept, because %s is not a relevant sub category.", sub_category)

    # Check whether "Tunnus" has value "LENNUNDUS"
    features = concept.findall(".//descrip[@type='Tunnus']")

    for f in features:
        feature = ET.tostring(f, encoding="unicode", method="text").strip()
        if "LENNUNDUS" in feature:
            logger.debug("This is aviation concept, it has LENNUNDUS for \"Tunnus\"")
            return True
        else:
            logger.debug("This is not an aviation concept, it has %s for \"Tunnus\"", feature)
            return False


# Returns concept type (concept, source, domain)
def concept_type(concept):
    concept_type = "concept"
    for languageGrp in concept.findall("./languageGrp"):
        if languageGrp.find("language").attrib["type"] == "Allikas":
            concept_type = "source"
        elif languageGrp.find("language").attrib["type"] == "Valdkond":
            concept_type = "domain"
    return concept_type


# Find all attribute "type" values for element "language"
def find_all_language_types(root):
    all_language_types = []
    for term in root.findall(".//languageGrp"):
        for language_type in term.findall(".//language"):
            all_language_types.append(language_type.attrib["type"])

    set_lang_types = set(all_language_types)
    unique_language_types = (list(set_lang_types))

    return unique_language_types
