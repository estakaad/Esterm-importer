import xml.etree.ElementTree as ET
import log_config
import data_classes
from lxml import etree
from langdetect import detect
import re

logger = log_config.get_logger()


# Find term"s or definition"s languages and match it with
# the language abbreviation used in API
def match_language(lang):
    lang_name = 'est'
    if lang == "FR":
        lang_name = "fra"
    if lang == "EN-GB":
        lang_name = "eng"
    if lang == "EN":
        lang_name = "eng"
    if lang == "ET":
        lang_name = "est"
    if lang == "FI":
        lang_name = "fin"
    if lang == "RU":
        lang_name = "rus"
    if lang == "XO":
        lang_name = "xho"
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
    if any("TR8" in ET.tostring(i, encoding="unicode", method="text") for i in domain_references):
        logger.debug("This is aviation concept, because \"Valdkonnaviide\" contains \"TR8\"")
        return True

    # Check whether "Alamvaldkond_" contains value which is present in the list of aviation sub categories
    sub_categories = concept.findall(".//descrip[@type='Alamvaldkond_']")

    for s in sub_categories:
        sub_category = ET.tostring(s, encoding="unicode", method="text").strip()
        if sub_category in sub_categories_list:
            logger.debug("This is aviation concept, because %s is a relevant sub category.", sub_category)
            return True
    if sub_categories:
        logger.debug("This is not aviation concept, none of the sub categories matched")

    # Check whether "Tunnus" has value "LENNUNDUS"
    features = concept.findall(".//descrip[@type='Tunnus']")

    if any("LENNUNDUS" in ET.tostring(f, encoding="unicode", method="text").strip() for f in features):
        logger.debug("This is aviation concept, it has LENNUNDUS for \"Tunnus\"")
        return True
    logger.debug("This is not an aviation concept, none of the conditions matched")

    return False


# Decide whether the concept will be added to the general list of concepts, list of aviation concepts or
# list of sources
def type_of_concept(conceptGrp):
    if conceptGrp.xpath('languageGrp/language[@type="Allikas"]'):
        type_of_concept = 'source'
    elif conceptGrp.xpath('languageGrp/language[@type="Valdkond"]'):
        type_of_concept = 'domain'
    elif is_concept_aviation_related(conceptGrp):
        type_of_concept = 'aviation'
    else:
        type_of_concept = 'general'
    logger.debug('Type of concept: %s', type_of_concept)
    return type_of_concept


# Find all attribute "type" values for element "language"
def find_all_language_types(root):
    all_language_types = []
    for term in root.findall(".//languageGrp"):
        for language_type in term.findall(".//language"):
            all_language_types.append(language_type.attrib["type"])

    set_lang_types = set(all_language_types)
    unique_language_types = (list(set_lang_types))

    return unique_language_types


def find_max_number_of_definitions(root):
    # Find all elements with attribute "type" and value "definitsioon"
    elements = root.findall(".//*[@type='definitsioon']")

    # Iterate through the elements and print their tag name and text content
    for element in elements:
        print(element.tag, element.text)


def is_type_word_type(descrip_text):
    if descrip_text == 'lühend':
        return True

def parse_word_types(descrip_text):
    if descrip_text == 'lühend':
        return 'l'


def parse_value_state_codes(descrip_text, count):
    code = None
    # Kui keelenditüüp on 'eelistermin' ja languageGrp element sisaldab rohkem kui üht termGrp elementi,
    # tuleb Ekilexis väärtusoleku väärtuseks salvestada 'eelistatud'
    if descrip_text == 'eelistermin' and count > 1:
        code = 'eelistatud'
    # Kui keelenditüüp on 'sünonüüm' ja termin on kohanimi, tuleb Ekilexis väärtusolekuks
    # salvestada 'mööndav'. Kui keelenditüüp on 'sünonüüm' ja termin ei ole kohanimi, siis Ekilexis ?
    elif descrip_text == 'sünonüüm':
        code = 'mööndav'
    # Kui keelenditüüp on 'variant', siis Ekilexis väärtusolekut ega keelenditüüpi ei salvestata.
    elif descrip_text == 'variant':
        code = 'variant'
    # Kui keelenditüüp on 'endine', tuleb Ekilexis väärtusoleku väärtuseks salvestada 'endine'
    elif descrip_text == 'endine':
        code = 'endine'
    # Kui keelenditüüp on 'väldi', tuleb Ekilexis väärtusoleku väärtuseks salvestada 'väldi'
    elif descrip_text == 'väldi':
        code = 'väldi'
    else:
        return None

    logger.debug('Value state code: %s.', code)

    return code


def parse_definition(descrip_text, descripGrp, lang):
    if descripGrp.xpath('descrip/xref'):
        source = descripGrp.xpath('descrip/xref')[0].text
    else:
        source = None

    if '[' in descrip_text:
        definition_text = descrip_text.split('[')[0].strip()
    else:
        definition_text = descrip_text.strip()

    definition = data_classes.Definition(
        value=definition_text,
        lang=lang,
        definitionTypeCode='definitsioon'
    )

    logger.info('Added definition - definition value: %s, language: %s', definition.value, definition.lang)

    return definition



# Kui /mtf/conceptGrp/languageGrp/termGrp/descripGrp/descrip[@type="Märkus"] alguses on
# "SÜNONÜÜM: ", "VARIANT: " või "ENDINE: ", siis tuleb see salvestada selle termGrp
# elemendi märkuseks, mille keelenditüüp Estermis on "SÜNONÜÜM", "VARIANT" või "ENDINE"
def update_notes(words):
    prefix_to_state_code = {
        "SÜNONÜÜM: ": "sünonüüm",
        "VARIANT: ": "variant",
        "ENDINE: ": "endine",
        "VÄLDI: ": "väldi",
        "VLDI: ": "väldi"
    }

    notes_to_move = {code: [] for code in prefix_to_state_code.values()}

    for word in words:
        for lexemeNote in word.lexemeNotes[:]:
            for prefix, state_code in prefix_to_state_code.items():
                if lexemeNote.value.startswith(prefix):
                    cleaned_note = lexemeNote.value.replace(prefix, "", 1)
                    lexemeNote.value = cleaned_note # Update the note value in place
                    notes_to_move[state_code].append(lexemeNote)
                    word.lexemeNotes.remove(lexemeNote)
                    logger.debug('Removed note from word: %s', word.value)
    for word in words:
        if word.lexemeValueStateCode in notes_to_move:
            word.lexemeNotes.extend(notes_to_move[word.lexemeValueStateCode])
            logger.debug('Added note to word: %s', word.value)

    return words



def are_terms_public(conceptGrp):
    if conceptGrp.xpath('system[@type="entryClass"]')[0].text == 'töös':
        return False
    elif conceptGrp.xpath('system[@type="entryClass"]')[0].text == 'määramata':
        return False
    elif conceptGrp.xpath('system[@type="entryClass"]')[0].text == 'avalik':
        return True


def get_description_value(descrip_element):
    descrip_element_value = ET.tostring(descrip_element, encoding='utf-8', method='xml').decode()
    start = descrip_element_value.index('>') + 1
    end = descrip_element_value.rindex('<')
    note_value = descrip_element_value[start:end]
    return note_value


def detect_language(note):
    if 'on kehtetu' in note:
        language = 'est'
    elif 'on kursiivis' in note:
        language = 'est'
    elif 'esineb' in note:
        language = 'est'
    else:
        try:
            language = detect(note)
            language = match_language(language.upper())
        except:
            language = 'est'

    return language


def extract_definition_source_link(definition):
    pattern = r'\[([^\[\]]*)\]$'
    match = re.search(pattern, definition.value)

    if match:
        # Extract source links
        links_text = match.group(1).strip()
        links = [item.strip() for item in links_text.split(';')]

        # Append source links to the definition's sourceLinks
        for link in links:
            definition.sourceLinks.append(data_classes.sourceLink(value=link))

        # Update the definition value to strip off the source link data
        definition.value = re.sub(pattern, '', definition.value).strip()

    return definition
