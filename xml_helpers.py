import logging
import inspect
import xml.etree.ElementTree as ET
import expert_sources_helpers
import log_config
from langdetect import detect
import re
import data_classes
import json
import regex


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


# Decide whether the concept will be added to the general list of concepts, list of aviation concepts or
# list of sources
def type_of_concept(conceptGrp):
    if conceptGrp.xpath('languageGrp/language[@type="Allikas"]'):
        type_of_concept = 'source'
    elif conceptGrp.xpath('languageGrp/language[@type="Valdkond"]'):
        type_of_concept = 'domain'
    else:
        type_of_concept = 'general'

    logger.debug('Type of concept: %s', type_of_concept)

    return type_of_concept


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
                    lexemeNote.value = cleaned_note  # Update the note value in place
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


##################################
## Word "Kontekst" > word.usage ##
##################################

# Returns the usage ("Kontekst") value without the source link + sourcelinks
def extract_usage_and_its_sourcelink(element, updated_sources, expert_names_to_ids_map):
    source_links = []
    concept_notes = []
    expert_source_found = False

    full_text = ''.join(element.itertext())
    usage_value, source_info = full_text.split('[', 1) if '[' in full_text else (full_text, '')
    usage_value = usage_value.strip()
    source_info = source_info.strip()
    source_info = source_info.rstrip(']')

    xref_element = element.find('.//xref')
    source_value = xref_element.text.strip() if xref_element is not None else ''
    if source_value == 'PakS-2021/05/02':
        source_value = 'PakS-2021/05/2'
    source_link_name = None

    # 'Abiteenistujatele laienevad töölepingu seadus ja muud tööseadused niivõrd,
    # kuivõrd käesoleva seaduse või avalikku teenistust reguleerivate eriseadustega
    # ei sätestata teisiti. [<xref Tlink="Allikas:X0002">X0002</xref> §13-2]'
    if xref_element is not None and xref_element.tail:
        source_link_name = xref_element.tail.strip()

    # 'Parents who are raising children have the right to assistance from the state. [77184]'
    elif source_info:
        source_value = source_info

    name = source_link_name if source_link_name else ''

    if 'PÄRING' in source_value:
        expert_source_found = True
        expert_name = source_info.replace('PÄRING', '').strip('{} ')
        expert_type = 'Päring'

        source_links.append(
            data_classes.Sourcelink(sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type(expert_name, expert_type, expert_names_to_ids_map),
                                    value='Päring',
                                    name=''))

    if 'DGT' in source_value:
        expert_source_found = True
        expert_name = source_info.replace('DGT', '').strip().strip('{}')
        expert_type = 'DGT'

        source_links.append(
            data_classes.Sourcelink(sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type(expert_name, expert_type, expert_names_to_ids_map),
                                    value='DGT',
                                    name=''))

    if 'PARLAMENT' in source_value:
        expert_source_found = True
        expert_name = source_info.replace('PARLAMENT', '').strip(' {}')
        expert_type = 'Parlament'

        source_links.append(
            data_classes.Sourcelink(sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type(expert_name, expert_type, expert_names_to_ids_map),
                                    value='Parlament',
                                    name=''))

    if 'CONSILIUM' in source_value:
        expert_source_found = True
        expert_name = source_info.replace('CONSILIUM', '').strip(' {}')
        expert_type = 'Consilium'
        source_links.append(
            data_classes.Sourcelink(sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type(expert_name, expert_type, expert_names_to_ids_map),
                                    value='Consilium',
                                    name=''))

    if 'EKSPERT' in source_value:
        expert_source_found = True
        expert_name = source_info.replace('EKSPERT', '').strip(' {}')
        expert_type = 'Ekspert'
        source_links.append(
            data_classes.Sourcelink(sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type(expert_name, expert_type, expert_names_to_ids_map),
                                    value='Ekspert',
                                    name=''))

    else:
        if source_value and not expert_source_found:
            if '§' in source_value:
                value = re.split(r'§', source_value, 1)[0].strip()
                name = "§ " + re.split(r'§', source_value, 1)[1].strip()
                source_links.append(
                    data_classes.Sourcelink(sourceId=find_source_by_name(updated_sources, value),
                                            value=value,
                                            name=name.strip(']')))
            elif ',' in source_value:
                value = re.split(r',', source_value, 1)[0].strip()
                name = re.split(r',', source_value, 1)[1].strip()
                source_links.append(
                    data_classes.Sourcelink(sourceId=find_source_by_name(updated_sources, value),
                                            value=value,
                                            name=name.strip(']')))
            elif source_value.startswith('BRITANNICA '):
                value = 'BRITANNICA'
                name = source_value.replace('BRITANNICA ', '')
                source_links.append(
                    data_classes.Sourcelink(sourceId=find_source_by_name(updated_sources, value),
                                            value=value,
                                            name=name.strip(']')))
            elif source_value.startswith('T40766 '):
                value = 'T40766'
                name = source_value.replace('T40766 ', '')
                source_links.append(
                    data_classes.Sourcelink(sourceId=find_source_by_name(updated_sources, value),
                                            value=value,
                                            name=name.strip(']')))
            else:
                source_links.append(
                    data_classes.Sourcelink(sourceId=find_source_by_name(updated_sources, source_value),
                                            value=source_value,
                                            name=name.strip(']')))

    return usage_value, source_links


######################################
## Concept "Märkus" > concept.notes ##
######################################

# Does the note contain examples in multiple languages? If so, it has to be split
def does_note_contain_multiple_languages(note):
    pattern = r'[A-Z]{2}:'

    if re.search(pattern, note):
        return True
    else:
        return False


def edit_note_with_multiple_languages(note):
    # 1. Replace [<xref Tlink="some_value_here">VALUE_HERE</xref> ANYTHING_HERE]\n with
    # [<xref Tlink="some_value_here">VALUE_HERE</xref> ANYTHING_HERE].
    pattern1 = r'(\[.*?\])\s*\n'
    replace1 = r'\1. '
    note = re.sub(pattern1, replace1, note)

    # 2. Replace [<xref Tlink="some_value_here">VALUE_HERE</xref> ANYTHING_HERE] with [VALUE_HERE ANYTHING_HERE]
    pattern2 = r'<xref Tlink=".*?">(.*?)</xref>'
    replace2 = r"\1"

    # Loop until no more patterns are found
    while re.search(pattern2, note):
        note = re.sub(pattern2, replace2, note)

    return note


######################################
## Sources ##
######################################

# Preprocess sources with ID-s, because otherwise it will take forever to find the match between name and ID
# Not sure if there are duplicate names, but just in case there are, let's map the name to a list of matching ID-s
def create_name_to_id_mapping(sources):
    name_to_ids = {}
    for source in sources:
        source_id = source['id']
        logger.info(f"Processing source ID: {source_id}")
        for prop in source['sourceProperties']:
            prop_type = prop['type']
            prop_value = prop['valueText']
            logger.info(f"  Prop type: {prop_type}, Prop value: {prop_value}")
            if prop_type == 'SOURCE_NAME':
                name = prop_value
                if name in name_to_ids:
                    name_to_ids[name].append(source_id)
                else:
                    name_to_ids[name] = [source_id]

    return name_to_ids


# Return ID if there is exactly one match. Return None, if there are 0 matches or more than one matches.
def find_source_by_name(name_to_ids_map, name):
    if name:
        name = name.strip('[]')

    source_ids = name_to_ids_map.get(name)

    if source_ids is None:
        logger.warning(f"Warning: Source ID for '{name}' not found.")

        if name is not None:
            caller_name = inspect.currentframe().f_back.f_code.co_name
            #print(f"Called from: {caller_name}")
            #print(name)

        # If none found, return ID of test source or otherwise concept won't be saved in Ekilex
        return '53385'

    # Now check for length
    if len(source_ids) == 1:
        logger.info(f"Source ID for '{name}' is {source_ids[0]}")
        return source_ids[0]
    else:
        logger.warning(f"Warning: Duplicate entries found for '{name}', using the first.")
        return source_ids[0]


def map_initials_to_names(initials):

    names_and_initials = {
        "super": "Import",
        "ALS": "Aime Liimets",
        "ARU": "Ann Rahnu",
        "ALK": "Anna-Liisa Kurve",
        "AAS": "Anne Annus",
        "AKS": "Anne Kaps",
        "AJK": "Annely Jauk",
        "ATM": "Anu Tähemaa",
        "AST": "Argo Servet",
        "AAA": "Arno Altoja",
        "DCS": "David Cousins",
        "EEU": "Epp Ehasalu",
        "EKS": "Epp Kirss",
        "EVA": "Eva Viira",
        "HNS": "Helen Niidas",
        "HTS": "Helin Teras",
        "HTN": "Helve Trumann",
        "HTM": "Hiie Tamm",
        "HSR": "Hille Saluäär",
        "IKF": "Indrek Koff",
        "ISL": "Ingrid Sibul",
        "IPU": "Irja Pärnapuu",
        "JMP": "Jaanika Müürsepp",
        "KVA": "Kai Vassiljeva",
        "KMA": "Kai-Maarja Lauba",
        "KMU": "Kairi Mesipuu",
        "LOA": "Katre-Liis Ojamaa",
        "KSI": "Kaupo Susi",
        "KTR": "Kristjan Teder",
        "KLK": "Krõõt Liivak",
        "KMR": "Küllike Maurer",
        "LLK": "Lembit Luik",
        "LKA": "Liina Kesküla",
        "LPK": "Liina Pohlak",
        "MVR": "Madis Vunder",
        "MHE": "Mae Hallistvee",
        "MLU": "Mai Lehtpuu",
        "MLR": "Mall Laur",
        "MKN": "Malle Klaassen",
        "MML": "Mare Maxwell",
        "MRS": "Mari Remmelgas",
        "MVS": "Mari Vaus",
        "MIA": "Merit Ilja",
        "OTP": "Oleg Toompuu",
        "PSK": "Piret Suurvarik",
        "RRS": "Raivo Rammus",
        "RNE": "Rita Niineste",
        "RSR": "Rita Sagur",
        "SRL": "Saule Reitel",
        "SCS": "Signe Cousins",
        "SES": "Signe Saar",
        "TKK": "Taima Kiisverk",
        "TKB": "Tarmo Kuub",
        "TMA": "Tarmo Milva",
        "TAR": "Tiina Agur",
        "UMK": "Urmas Maranik",
        "UKS": "Urve Karuks",
        "UKO": "Urve Kiviloo",
        "VJS": "Virge Juurikas",
        "ÜMT": "Ülle Männart",
        "AMS": "Anu Murakas",
        "IKK": "Inga Kukk",
        "KLA": "Kadi-Liis Aun",
        "KKD": "Kairi Kivilaid",
        "KMO": "Kristel Merilo",
        "KWM": "Kristel Weidebaum",
        "LVR": "Liis Variksaar",
        "LEU": "Liisi Erepuu",
        "PMS": "Priit Milius",
        "RRP": "Riho Raudsepp",
        "TUL": "Tanel Udal",
        "TPO": "Tatjana Peetersoo",
        "TKS": "Teet Kiipus",
        "TSR": "Terje Soomer",
        "TVN": "Tiina Veberson",
        "TRE": "Triin Randlane",
        "TMU": "Toomas Muru",
        "MPO": "Merily Plado",
        "KKA": "Kaisa Kesküla",
        "ÜAU": "Ülle Allsalu",
        "ETM": "Eva Tamm",
        "KJN": "Kairi Janson",
        "EPD": "Elice Paemurd",
        "KAN": "Kadi-Liis Aun"
    }

    return names_and_initials.get(initials, initials)


##########################################
## "Definitsioon" > concept.definitions ##
##########################################


def handle_definition(definition_element_value, name_to_id_map, language, expert_names_to_ids_map):

    if definition_element_value.startswith('any trailer designed'):
        print(definition_element_value)

    split_definitions = [definition for definition in re.split(r'\d+\.\s', definition_element_value) if definition]

    match_links_pattern = r'(?<!^)\[[^[]+\]'

    final_definitions = []

    for split_definition in split_definitions:
        split_definition = split_definition.strip().strip(';')
        match_links = re.findall(match_links_pattern, split_definition)

        source_links_for_definition = []

        if match_links:
            for link in match_links:
                split_definition = split_definition.replace(link, '')
                link = link.strip('[]')

                if ';' in link:
                    separate_links = re.split('; ', link)

                    for link in separate_links:

                        value, name, expert_name, expert_type = separate_sourcelink_value_from_name(link.strip())

                        if expert_type:
                            source_links_for_definition.append(data_classes.Sourcelink(
                                sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type(expert_name, expert_type, expert_names_to_ids_map),
                                value=expert_type,
                                name=''
                            ))
                        else:
                            source_links_for_definition.append(data_classes.Sourcelink(
                                sourceId=find_source_by_name(name_to_id_map, value),
                                value=value,
                                name=name
                            ))

                else:

                    value, name, expert_name, expert_type = separate_sourcelink_value_from_name(link.strip())

                    if expert_type:
                        source_links_for_definition.append(data_classes.Sourcelink(
                            sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type(expert_name,
                                                                                                  expert_type,
                                                                                                  expert_names_to_ids_map),
                            value=expert_type,
                            name=''
                        ))
                    elif name.startswith('TKP, '):
                        source_links_for_definition.append(data_classes.Sourcelink(
                            sourceId=find_source_by_name(name_to_id_map, 'TKP'),
                            value='TKP',
                            name=name.replace('TKP, ', '')
                        ))
                    elif name.startswith('WBS, '):
                        source_links_for_definition.append(data_classes.Sourcelink(
                            sourceId=find_source_by_name(name_to_id_map, 'WBS'),
                            value='WBS',
                            name=name.replace('WBS, ', '')
                        ))
                    elif name.startswith('ARV, '):
                        source_links_for_definition.append(data_classes.Sourcelink(
                            sourceId=find_source_by_name(name_to_id_map, 'ARV'),
                            value='ARV',
                            name=name.replace('ARV, ', '')
                        ))
                    elif name.startswith('T0057 '):
                        source_links_for_definition.append(data_classes.Sourcelink(
                            sourceId=find_source_by_name(name_to_id_map, 'T0057 '),
                            value='T0057 ',
                            name=name.replace('T0057 ', '')
                        ))
                    elif name.startswith('VSL, '):
                        source_links_for_definition.append(data_classes.Sourcelink(
                            sourceId=find_source_by_name(name_to_id_map, 'VSL'),
                            value='VSL',
                            name=name.replace('VSL, ', '')
                        ))
                    elif name.startswith('CDB, '):
                        source_links_for_definition.append(data_classes.Sourcelink(
                            sourceId=find_source_by_name(name_to_id_map, 'CDB'),
                            value='CDB',
                            name=name.replace('CDB, ', '')
                        ))
                    elif name.startswith('TTD, '):
                        source_links_for_definition.append(data_classes.Sourcelink(
                            sourceId=find_source_by_name(name_to_id_map, 'TTD'),
                            value='TTD',
                            name=name.replace('TTD, ', '')
                        ))
                    elif name.startswith('SIL, '):
                        source_links_for_definition.append(data_classes.Sourcelink(
                            sourceId=find_source_by_name(name_to_id_map, 'SIL'),
                            value='SIL',
                            name=name.replace('SIL, ', '')
                        ))
                    elif name.startswith('TER, '):
                        source_links_for_definition.append(data_classes.Sourcelink(
                            sourceId=find_source_by_name(name_to_id_map, 'TER'),
                            value='TER',
                            name=name.replace('TER, ', '')
                        ))
                    elif name.startswith('BRIONLINE, '):
                        source_links_for_definition.append(data_classes.Sourcelink(
                            sourceId=find_source_by_name(name_to_id_map, 'BRIONLINE'),
                            value='BRIONLINE',
                            name=name.replace('BRIONLINE, ', '')
                        ))
                    elif name.startswith('ESR, '):
                        print('esr: ' + name)
                        source_links_for_definition.append(data_classes.Sourcelink(
                            sourceId=find_source_by_name(name_to_id_map, 'ESR'),
                            value='ESR',
                            name=name.replace('ESR, ', '')
                        ))
                    elif name.startswith('PDE, '):
                        source_links_for_definition.append(data_classes.Sourcelink(
                            sourceId=find_source_by_name(name_to_id_map, 'PDE'),
                            value='PDE',
                            name=name.replace('PDE, ', '')
                        ))
                    elif value == 'A' and name == 'Dictionary':
                        source_links_for_definition.append(data_classes.Sourcelink(
                            sourceId=find_source_by_name(name_to_id_map, 'A Dictionary of Business and Management'),
                            value='A Dictionary of Business and Management',
                            name=''
                        ))
                    elif value == 'New' and name == 'Oxford':
                        source_links_for_definition.append(data_classes.Sourcelink(
                            sourceId=find_source_by_name(name_to_id_map, 'New Oxford American Dictionary'),
                            value='New Oxford American Dictionary',
                            name=''
                        ))
                    elif value == 'The' and name == 'Canadian':
                        source_links_for_definition.append(data_classes.Sourcelink(
                            sourceId=find_source_by_name(name_to_id_map, 'The Canadian Oxford Dictionary'),
                            value='The Canadian Oxford Dictionary',
                            name=''
                        ))
                    elif value == 'American' and name == 'Heritage®':
                        source_links_for_definition.append(data_classes.Sourcelink(
                            sourceId=find_source_by_name(name_to_id_map, 'American Heritage® Dictionary of the English Language'),
                            value='American Heritage® Dictionary of the English Language',
                            name=''
                        ))
                    elif name.startswith('VÕS, '):
                        source_links_for_definition.append(data_classes.Sourcelink(
                            sourceId=find_source_by_name(name_to_id_map, 'VÕS'),
                            value='VÕS',
                            name=name.replace('VÕS, ', '')
                        ))
                    elif name.startswith('AKS, '):
                        source_links_for_definition.append(data_classes.Sourcelink(
                            sourceId=find_source_by_name(name_to_id_map, 'AKS'),
                            value='AKS',
                            name=name.replace('AKS, ', '')
                        ))
                    elif name.startswith('ODC, '):
                        source_links_for_definition.append(data_classes.Sourcelink(
                            sourceId=find_source_by_name(name_to_id_map, 'ODC'),
                            value='ODC',
                            name=name.replace('ODC, ', '')
                        ))
                    elif name.startswith('ÕS, '):
                        source_links_for_definition.append(data_classes.Sourcelink(
                            sourceId=find_source_by_name(name_to_id_map, 'ÕS'),
                            value='ÕS',
                            name=name.replace('ÕS, ', '')
                        ))
                    elif name.startswith('BRI, '):
                        source_links_for_definition.append(data_classes.Sourcelink(
                            sourceId=find_source_by_name(name_to_id_map, 'BRI'),
                            value='BRI',
                            name=name.replace('BRI, ', '')
                        ))
                    elif name.startswith('OMD, '):
                        source_links_for_definition.append(data_classes.Sourcelink(
                            sourceId=find_source_by_name(name_to_id_map, 'OMD'),
                            value='OMD',
                            name=name.replace('OMD, ', '')
                        ))
                    elif name.startswith('MED, '):
                        source_links_for_definition.append(data_classes.Sourcelink(
                            sourceId=find_source_by_name(name_to_id_map, 'MED'),
                            value='MED',
                            name=name.replace('MED, ', '')
                        ))
                    else:
                        source_links_for_definition.append(data_classes.Sourcelink(
                            sourceId=find_source_by_name(name_to_id_map, value),
                            value=value,
                            name=name
                        ))
        else:
            continue

        final_definitions.append(data_classes.Definition(
            value=split_definition.strip(),
            lang=language,
            definitionTypeCode='definitsioon',
            sourceLinks=source_links_for_definition
            )
        )

    return final_definitions


def separate_sourcelink_value_from_name(sourcelink):

    expert_name = None
    expert_type = None

    match_comma = re.search(r'(\d*,)', sourcelink)

    if bool(re.match(r'^X\d{4}\s', sourcelink)):
        if len(sourcelink) > 5:
            value = sourcelink[:5]
            name = sourcelink.replace(sourcelink[:6], '')
        else:
            value = sourcelink
            name = ''
    elif bool(re.match(r'^X\d{4},', sourcelink)):
        if len(sourcelink) > 5:
            value = sourcelink[:5]
            name = sourcelink.replace(sourcelink[:5], '')
        else:
            value = sourcelink
            name = ''
    elif bool(re.match(r'^X\d{4}-', sourcelink)):
        value = sourcelink[:5]
        name = sourcelink.replace(sourcelink[:6], '')
    elif bool(re.match(r'^X\d{5}-', sourcelink)):
        value = sourcelink[:6]
        name = sourcelink[6:]
    elif bool(re.match(r'^X\d{5},', sourcelink)):
        value = sourcelink[:6]
        name = sourcelink.replace(value + ', ', '')
    elif bool(re.match(r'^\d{5}\s,', sourcelink)):
        if len(sourcelink) > 5:
            value = sourcelink[:5]
            name = sourcelink.replace(sourcelink[:6], '')
        else:
            value = sourcelink
            name = ''
    elif bool(re.match(r'^\d{5}-', sourcelink)):
        if len(sourcelink) > 5:
            value = sourcelink[:5]
            name = sourcelink.replace(sourcelink[:5], '')
        else:
            value = sourcelink
            name = ''
    elif bool(re.match(r'^\d{5}-,', sourcelink)):
        if len(sourcelink) > 5:
            value = sourcelink[:5]
            name = sourcelink.replace(sourcelink[:5], '')
    elif bool(re.match(r'^X.{6},', sourcelink)):
        if len(sourcelink) > 7:
            value = sourcelink[:7]
            name = sourcelink.replace(sourcelink[:7], '')
        else:
            value = sourcelink
            name = ''
    elif bool(re.match(r'^GG\d{3}-', sourcelink)):
        if len(sourcelink) > 5:
            value = sourcelink[:5]
            name = sourcelink.replace(sourcelink[:5], '')
        else:
            value = sourcelink
            name = ''
    elif bool(re.match(r'^X\d{4}E', sourcelink)):
        if len(sourcelink) > 7:
            value = sourcelink[:7]
            name = sourcelink.replace(sourcelink[:7], '')
        else:
            value = sourcelink
            name = ''
    elif bool(re.match(r'^X\d{5}E', sourcelink)):
        if len(sourcelink) > 7:
            value = sourcelink[:7]
            name = sourcelink.replace(sourcelink[:7], '')
        else:
            value = sourcelink
            name = ''
    elif bool(re.match(r'^X\d{5}\s', sourcelink)):
        if len(sourcelink) > 6:
            value = sourcelink[:6]
            name = sourcelink.replace(sourcelink[:7], '')
        else:
            value = sourcelink
            name = ''
    elif sourcelink.startswith('FCL DRAFT REG'):
        if sourcelink == 'FCL DRAFT REG':
            value = 'FCL DRAFT REG'
            name = ''
        else:
            value = 'FCL DRAFT REG'
            name = sourcelink.replace('FCL DRAFT REG ', '')
    elif sourcelink.startswith('PakS-2021/05/02'):
        value = 'PakS-2021/05/2'
        name = sourcelink.replace('PakS-2021/05/02 ', '')
    elif sourcelink.startswith('K80050 '):
        value = 'K80050'
        name = sourcelink.replace('K80050 ', '')
    elif '§' in sourcelink:
        value = re.split(r'§', sourcelink, 1)[0].strip()
        name = "§ " + re.split(r'§', sourcelink, 1)[1].strip()
    elif 'ConvRT ' in sourcelink:
        value = 'ConvRT'
        name = sourcelink.replace('ConvRT ', '')
    elif sourcelink.startswith('MRS'):
        value = sourcelink
        name = ''
    elif sourcelink == 'EVS 911:2018':
        value = sourcelink
        name = ''
    elif sourcelink.startswith('EVS: EN '):
        value = sourcelink
        name = ''
    elif sourcelink.startswith('EKN, '):
        value = 'EKN'
        name = sourcelink.replace('EKN, ', '')
    elif sourcelink.startswith('TSR, '):
        value = 'TSR'
        name = sourcelink.replace('TSR, ', '')
    elif sourcelink.startswith('TEK, '):
        value = 'TEK'
        name = sourcelink.replace('TEK, ', '')
    elif sourcelink.startswith('32002R2320 '):
        value = '32002R2320'
        name = sourcelink.replace('32002R2320 ', '')
    elif sourcelink == 'PEL T 2-2013':
        value = sourcelink
        name = ''
    elif sourcelink == 'EDD 2016/028/R':
        value = sourcelink
        name = ''
    elif sourcelink == 'ASM käsiraamat':
        value = sourcelink
        name = ''
    elif sourcelink.startswith('SMT, '):
        value = 'SMT'
        name = sourcelink.replace('SMT, ', '')
    elif sourcelink.startswith('MKM 8.03.2011 nr 20 '):
        value = 'MKM 8.03.2011 nr 20'
        name = sourcelink.replace('MKM 8.03.2011 nr 20 ', '')
    elif 'Electropedia, ' in sourcelink:
        value = 'Electropedia'
        name = sourcelink.replace('Electropedia, ', '')
    elif sourcelink == 'OPS T 1-2 M1':
        value = sourcelink
        name = ''
    elif sourcelink == 'LEND JA PLANEERIMINE':
        value = sourcelink
        name = ''
    elif sourcelink == 'VV 16.06.2011 nr 78':
        value = sourcelink
        name = ''
    elif sourcelink == 'UAV reeglid':
        value = sourcelink
        name = ''
    elif sourcelink.startswith('LES, '):
        value = 'LES'
        name = sourcelink.replace('LES, ', '')
    elif sourcelink.startswith('Choosing a Business'):
        value = 'Choosing a Business Model That Will Grow Your Company'
        name = sourcelink.replace('Choosing a Business Model That Will Grow Your Company', '')
    elif 'wiktionary.org' in sourcelink:
        value = 'WIKTIONARY'
        name = sourcelink
    elif 'WIKIPEDIA ' in sourcelink:
        value = 'WIKIPEDIA'
        name = sourcelink.replace('WIKIPEDIA ', '')
    elif 'Wikipedia, ' in sourcelink:
        value = 'WIKIPEDIA'
        name = sourcelink.replace('Wikipedia, ', '')
    elif 'Wikipedia, ' in sourcelink:
        value = 'WIKIPEDIA'
        name = sourcelink.replace('Wikipedia, ', '')
    elif sourcelink == 'Wikipedia':
        value = 'WIKIPEDIA'
        name = ''
    elif 'webopedia' in sourcelink:
        value = 'Webopedia'
        name = sourcelink
    elif sourcelink == 'A Dictionary of the Internet':
        value = sourcelink
        name = ''
    elif 'MER,' in sourcelink:
        value = 'MER'
        name = sourcelink.replace('MER, ', '')
    elif 'techopedia' in sourcelink:
        value = 'Techopedia: Dictionary'
        name = sourcelink
    elif 'Investopedia, Scalability' in sourcelink:
        value = 'Investopedia, Scalability'
        name = sourcelink.replace('Investopedia, Scalability', '')
    elif 'BLA7,' in sourcelink:
        value = 'BLA7'
        name = sourcelink.replace('BLA7, ', '')
    elif sourcelink == 'ETSI EN 301 040 V2.1.1':
        value = 'ETSI EN 301 040 V2.1.1'
        name = ''
    elif sourcelink.startswith('ONT, '):
        value = 'ONT'
        name = sourcelink.replace('ONT, ', '')
    elif sourcelink == 'LLT AS-WWW':
        value = 'LLT AS-WWW'
        name = ''
    elif sourcelink.startswith('EKS, '):
        value = 'EKS'
        name = sourcelink.replace('EKS, ', '')
    elif sourcelink.startswith('AIR OPS-'):
        value = sourcelink
        name = ''
    elif sourcelink.startswith('EUR, '):
        value = 'EUR'
        name = sourcelink.replace('EUR, ', '')
    elif sourcelink.startswith('MAV, '):
        value = 'MAV'
        name = sourcelink.replace('MAV, ', '')
    elif sourcelink.startswith('ARV:'):
        value = 'ARV'
        name = sourcelink.replace('ARV: ', '')
    elif sourcelink.startswith('RVMS '):
        value = 'RVMS'
        name = sourcelink.replace('RVMS ', '')
    elif sourcelink.startswith('TEH, '):
        value = 'TEH'
        name = sourcelink.replace('TEH, ', '')
    elif sourcelink == 'AIR OPS-AMC&amp;GM':
        value = 'AIR OPS-AMC&amp;GM'
        name = ''
    elif sourcelink.startswith('T1064 '):
        value = 'T1064'
        name = sourcelink.replace('T1064 ', '')
    elif sourcelink.startswith('T2269 '):
        value = 'T2269'
        name = sourcelink.replace('T2269 ', '')
    elif 'BLA,' in sourcelink:
        value = 'BLA'
        name = sourcelink.replace('BLA, ', '')
    elif 'AMS ' in sourcelink:
        value = sourcelink
        name = ''
    elif 'ENE,' in sourcelink:
        value = 'ENE'
        name = sourcelink.replace('ENE, ', '')
    elif sourcelink.startswith('ÜRO '):
        value = sourcelink
        name = ''
    elif sourcelink.startswith('Aquatic '):
        value = sourcelink
        name = ''
    elif sourcelink.startswith('JARUS '):
        value = sourcelink
        name = ''
    elif 'OED ' in sourcelink:
        value = 'OED'
        name = sourcelink.replace('OED ', '')
    elif 'OED,' in sourcelink:
        value = 'OED'
        name = sourcelink.replace('OED', '')
    elif 'B 737 OM' in sourcelink:
        value = sourcelink
        name = ''
    elif 'EVS-EN 45020:2008 ' in sourcelink:
        value = 'EVS-EN 45020:2008'
        name = sourcelink.replace('EVS-EN 45020:2008 ', '')
    elif '32006R0562 ' in sourcelink:
        value = '32006R0562'
        name = sourcelink.replace('32006R0562 ', '')
    elif sourcelink.startswith('X50043'):
        value = 'X50043'
        name = sourcelink.replace('X50043 ', '')
    elif sourcelink.startswith('EVS 758:2009'):
        value = sourcelink
        name = ''
    elif sourcelink == 'PPA-ekspert':
        value = sourcelink
        name = ''
    elif bool(re.match(r'^T\d{5}', sourcelink)):
        if len(sourcelink) > 6:
            value = sourcelink[:6]
            name = sourcelink.replace(sourcelink[:6], '')
        else:
            value = sourcelink
            name = ''
    elif bool(re.match(r'^T\d{4}\,', sourcelink)):
        value = sourcelink[:5]
        name = sourcelink.replace(sourcelink[:7], '')
    elif sourcelink == 'LLT AS-EKSPERT':
        value = 'LLT AS-EKSPERT'
        name = ''
    elif sourcelink == 'MA-EKSPERT':
        value = 'MA-EKSPERT'
        name = ''
    elif sourcelink.replace('EKSPERT', '').strip(' {}').lower() == 'ants rsis':
        value = 'Ekspert'
        name = ''
        expert_name = 'Ants Ärsis'
        expert_type = 'Ekspert'
    elif 'EKSPERT' in sourcelink:
        value = 'Ekspert'
        name = ''
        expert_name = sourcelink.replace('EKSPERT', '').strip(' {}')
        if len(expert_name) > len('EKSPERT'):
            expert_name = sourcelink.replace('EKSPERT', '').strip(' {}')
            expert_type = 'Ekspert'
        else:
            expert_name = 'Ekspert'
            expert_type = 'Ekspert'
    elif 'PÄRING' in sourcelink:
        value = 'Päring'
        name = ''
        expert_name = sourcelink.replace('PÄRING ', '').strip(' {}')
        expert_type = 'Päring'
    elif 'DGT' in sourcelink:
        value = 'DGT'
        name = ''
        expert_name = sourcelink.replace('DGT', '').strip(' {}')
        expert_type = 'DGT'
    elif 'JURIST' in sourcelink:
        value = 'Jurist'
        name = ''
        expert_name = sourcelink.replace('JURIST', '').strip(' {}')
        expert_type = 'Jurist'
    elif 'CONSILIUM' in sourcelink:
        value = 'Consilium'
        name = ''
        expert_name = sourcelink.replace('CONSILIUM', '').strip(' {}')
        expert_type = 'Consilium'
    elif 'DELEST' in sourcelink:
        value = 'Delest'
        name = ''
        expert_name = sourcelink.replace('DELEST', '').strip(' {}')
        expert_type = 'Delest'
    elif sourcelink.startswith('ICAO'):
        if 'tõlge' in  sourcelink:
            value = sourcelink.replace(' tõlge', '')
            name = 'tõlge'
        else:
            value = sourcelink
            name = ''
    elif sourcelink.startswith('TET,'):
        value = 'TET'
        name = sourcelink.replace('TET, ', '')
    elif sourcelink.startswith('GG002'):
        value = 'GG002'
        name = sourcelink.replace('GG002', '')
    elif sourcelink.startswith('WPG'):
        value = 'WPG'
        name = sourcelink.replace('WPG', '')
    elif sourcelink.startswith('TSR '):
        value = 'TSR'
        name = sourcelink.replace('TSR ', '')
    elif sourcelink.startswith('TCC, '):
        value = 'TCC'
        name = sourcelink.replace('TCC, ', '')
    elif sourcelink.startswith('3656 '):
        value = '3656'
        name = sourcelink.replace('3656, ', '')
    elif sourcelink.startswith('MML, '):
        value = 'MML'
        name = sourcelink.replace('MML, ', '')
    elif sourcelink.startswith('4017 '):
        value = '4017'
        name = sourcelink.replace('4017 ', '')
    elif sourcelink.startswith('X40046'):
        value = 'X40046'
        name = sourcelink.replace('X40046', '')
    elif sourcelink.startswith('MKM 8.06.2005 nr 66 '):
        value = 'MKM 8.06.2005 nr 66'
        name = sourcelink.replace('MKM 8.06.2005 nr 66 ', '')
    elif sourcelink.startswith('X50028'):
        value = 'X50028'
        name = sourcelink.replace('X50028', '')
    elif sourcelink.startswith('T70629'):
        value = 'T70629'
        name = sourcelink.replace('T70629', '')
    elif sourcelink.startswith('EVS-ISO'):
        value = sourcelink
        name = ''
    elif sourcelink.startswith('X30073 '):
        value = 'X30073'
        name = sourcelink.replace('X30073 ', '')
    elif sourcelink.startswith('EVS-EN'):
        value = sourcelink
        name = ''
    elif sourcelink.startswith('ISO '):
        value = sourcelink
        name = ''
    elif sourcelink.startswith('A. '):
        value = sourcelink
        name = ''
    elif sourcelink.startswith('MKM '):
        value = sourcelink
        name = ''
    elif sourcelink.startswith('ESA 95 '):
        value = 'ESA 95'
        name = sourcelink.replace('ESA 95 ', '')
    elif sourcelink == 'GSFA Online':
        value = 'GSFA Online'
        name = ''
    elif sourcelink.startswith('ESA '):
        value = sourcelink
        name = ''
    elif sourcelink.startswith('Endic'):
        value = 'EnDic'
        name = ''
    elif sourcelink.startswith('GG003 '):
        value = 'GG003'
        name = sourcelink.replace('GG003', '')
    elif sourcelink.startswith('GG003,'):
        value = 'GG003'
        name = sourcelink.replace('GG003, ', '')
    elif sourcelink.startswith('KRM'):
        value = 'KRM'
        name = sourcelink.replace('KRM', '')
    elif sourcelink.startswith('JAR-OPS '):
        value = sourcelink
        name = ''
    elif sourcelink == 'JAR 1':
        value = 'JAR-1'
        name = ''
    elif sourcelink.startswith('JAR-FCL '):
        value = sourcelink
        name = ''
    elif 'tõlge' in sourcelink:
        value = sourcelink.replace(' tõlge', '')
        name = 'tõlge'
    elif sourcelink.startswith('JAR '):
        value = sourcelink
        name = ''
    elif sourcelink.startswith('AC '):
        value = sourcelink
        name = ''
    elif sourcelink.startswith('SAR '):
        value = sourcelink
        name = ''
    elif sourcelink.startswith('V00197, '):
        value = 'V00197'
        name = sourcelink.replace('V00197, ', '')
    elif sourcelink.startswith('LENNU '):
        value = sourcelink
        name = ''
    elif sourcelink.startswith('PART '):
        value = sourcelink
        name = ''
    elif sourcelink.startswith('MRL,'):
        value = 'MRL'
        name = sourcelink.replace('MRL, ', '')
    elif sourcelink.startswith('CN '):
        value = 'CN'
        name = sourcelink.replace('CN ', '')
    elif sourcelink.startswith('CN, '):
        value = 'CN'
        name = sourcelink.replace('CN, ', '')
    elif sourcelink.startswith('Cn '):
        value = 'CN'
        name = sourcelink.replace('Cn ', '')
    elif sourcelink.startswith('HIV/AIDS '):
        value = sourcelink
        name = ''
    elif sourcelink.startswith('ГОСТ '):
        value = sourcelink
        name = ''
    elif sourcelink.startswith('Eesti '):
        value = sourcelink
        name = ''
    elif sourcelink.startswith('T2026 '):
        value = 'T2026'
        name = sourcelink.replace('T2026 ', '')
    elif sourcelink.startswith('T1071 '):
        value = 'T1071'
        name = sourcelink.replace('T1071 ', '')
    elif sourcelink.startswith('VPL, '):
        value = 'VPL'
        name = sourcelink.replace('VPL, ', '')
    elif sourcelink.startswith('IRIS '):
        value = sourcelink
        name = ''
    elif sourcelink.startswith('Kaitsevägi'):
        value = sourcelink
        name = ''
    elif sourcelink.startswith('Aianduse '):
        value = sourcelink
        name = ''
    elif sourcelink.startswith('BRITANNICA '):
        value = 'BRITANNICA'
        name = sourcelink.replace('BRITANNICA ', '')
    elif sourcelink.startswith('AKS '):
        value = 'AKS'
        name = sourcelink.replace('AKS ', '')
    elif sourcelink.startswith('WHO '):
        value = sourcelink
        name = ''
    elif match_comma:
        value = match_comma.group(1).strip(',')
        name = sourcelink.replace(value, '').strip(',').strip()
    elif ' ' in sourcelink:
        parts = sourcelink.split(' ')
        value = parts[0]
        name = parts[1]
    else:
        value = sourcelink
        name = ''

    return value, name, expert_name, expert_type


##########################################
## Word "Märkus" > word.lexemenotes ##
## Concept "Märkus" > concept.notes ##
##########################################

def handle_notes_with_brackets(type, name_to_id_map, expert_sources_ids_map, term_sources_to_ids_map, note_raw):
    print(type)
    lexeme_notes = []
    concept_notes = []
    source_links = []

    # Case #0 :: Whole note is in {} :: {Konsulteeritud Välisministeeriumi tõlkeosakonnaga, KMU 16.11.2001} - OK - 17-11
    if note_raw.startswith('{'):
        print('Case #0: ' + note_raw)
        if note_raw.endswith('}'):
            if type == 'word':
                lexeme_notes.append(data_classes.Lexemenote(
                    value=note_raw.strip('{}'),
                    lang='est',
                    publicity=False,
                    sourceLinks=source_links
                ))
            elif type == 'concept':
                concept_notes.append(data_classes.Note(
                    value=note_raw.strip('{}'),
                    lang='est',
                    publicity=False,
                    sourceLinks=source_links
                ))
            else:
                print('error 1')

    # Case #1 :: no date :: no source ::
    # "ametnik, kellel on allkirjaõigus ja teatud kohtulahendite tegemise õigus" - ok
    elif not any(char in note_raw for char in "{}[]"):
        print('Case #1: ' + note_raw)
        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw,
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
            return lexeme_notes, concept_notes
        elif type == 'concept':
            concept_notes.append(data_classes.Note(
                value=note_raw,
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))

        else:
            print('error 2')

        return lexeme_notes, concept_notes

    elif "[ICAO" in note_raw and note_raw.endswith("]"):
        start_index = note_raw.rfind("[")
        # Check if "ICAO" is in the substring starting from the last '['
        if start_index != -1 and "ICAO" in note_raw[start_index:]:
            # Extract the value inside the brackets
            sourcelink_value = note_raw[start_index + 1:-1]
            source_links.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, sourcelink_value),
                value=sourcelink_value,
                name=''
            ))

            if type == 'word':
                lexeme_notes.append(data_classes.Lexemenote(
                    value=note_raw.replace('[' + sourcelink_value + ']', ''),
                    lang='est',
                    publicity=True,
                    sourceLinks=source_links
                ))
            elif type == 'concept':
                concept_notes.append(data_classes.Note(
                    value=note_raw.replace('[' + sourcelink_value + ']', ''),
                    lang='est',
                    publicity=True,
                    sourceLinks=source_links
                ))
            else:
                print('error icao')
        else:
            if type == 'word':
                lexeme_notes.append(data_classes.Lexemenote(
                    value='KONTROLLIDA: ' + note_raw,
                    lang='est',
                    publicity=False,
                    sourceLinks=source_links
                ))
            elif type == 'concept':
                concept_notes.append(data_classes.Note(
                    value='KONTROLLIDA: ' + note_raw,
                    lang='est',
                    publicity=False,
                    sourceLinks=source_links
                ))
            else:
                print('error x')

    # Case #2 :: no date :: source ::
    # "Nii Eesti kui ka ELi uutes kindlustusvaldkonna õigusaktides kasutatakse terminit kindlustusandja. [KTTG]" - ok
    elif not note_raw.strip('.')[-3:-1].isdigit():
        print('Case #2: ' + note_raw)
        # In case there are more than one [ in note, leave it be
        if note_raw.count('[') > 1:
            if type == 'word':
                lexeme_notes.append(data_classes.Lexemenote(
                    value='KONTROLLIDA: ' + note_raw,
                    lang='est',
                    publicity=False,
                    sourceLinks=source_links
                ))
            elif type == 'concept':
                concept_notes.append(data_classes.Note(
                    value='KONTROLLIDA: ' + note_raw,
                    lang='est',
                    publicity=False,
                    sourceLinks=source_links
                ))
            else:
                print('error 3')

            return lexeme_notes, concept_notes

        if note_raw.endswith('}'):
            parts = note_raw.split('{')
            parts = [part.strip() for part in parts]
            note = parts[0]
            source = parts[1].strip('}')

            key = (source, "Eesti Õiguskeele Keskuse terminoloog")
            source_id = term_sources_to_ids_map.get(key)
            source_links.append(data_classes.Sourcelink(
                sourceId=source_id,
                value=source,
                name=''
            ))

            if type == 'word':
                lexeme_notes.append(data_classes.Lexemenote(
                    value=note,
                    lang='est',
                    publicity=True,
                    sourceLinks=source_links
                ))
            elif type == 'concept':
                concept_notes.append(data_classes.Note(
                    value=note,
                    lang='est',
                    publicity=True,
                    sourceLinks=source_links
                ))
            else:
                print('error 2.1')

        else:

            parts = note_raw.split('[')
            note_value = parts[0].strip()

            sourcelink_value = parts[1].strip('[]') if len(parts) > 1 else ''
            sourcelink_name = None

            if ',' in sourcelink_value:
                print('kas läheb kaduma? ')
                parts = sourcelink_value.split(',')
                sourcelink_value = parts[0]
                sourcelink_name = parts[1].strip()

                if 'EKSPERT' in sourcelink_value:
                    full_source = sourcelink_value + ', ' + sourcelink_name
                    name = full_source.replace('EKSPERT ', '').strip()
                    name = name.replace('{}', '')
                    source_links.append(data_classes.Sourcelink(
                        sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type(name, 'Ekspert',
                                                                                              expert_sources_ids_map),
                        value='Ekspert',
                        name=''
                    ))
                else:
                    source_links.append(data_classes.Sourcelink(
                        sourceId=find_source_by_name(name_to_id_map, sourcelink_value),
                        value=sourcelink_value,
                        name=sourcelink_name
                    ))

            elif ';' in sourcelink_value:
                sources = sourcelink_value.split(';')
                for source in sources:
                    if 'EKSPERT' in source.strip():
                        name = source.replace('EKSPERT ', '').replace('{}', '').strip()
                        source_links.append(data_classes.Sourcelink(
                            sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type(name, 'Ekspert',
                                                                                                  expert_sources_ids_map),
                            value='Ekspert',
                            name=''
                        ))
                    elif bool(re.match(r'^[A-Z]{3}\s\d', source)):
                        match = re.match(r'^([A-Z]{3})', source)
                        if match:
                            key = (match.group(1).strip(), "Eesti Õiguskeele Keskuse terminoloog")
                            source_id = term_sources_to_ids_map.get(key)
                            source_links.append(data_classes.Sourcelink(
                                sourceId=source_id,
                                value=match.group(1).strip(),
                                name=''
                            ))
                        note_value = note_value + ' [' + source.replace(match.group(1), '').strip() + ']'
                    else:
                        source_links.append(data_classes.Sourcelink(
                            sourceId=find_source_by_name(name_to_id_map, source.strip()),
                            value=source.strip(),
                            name=''
                        ))
                    print(source_links)
            elif '§' in sourcelink_value:
                print('kontrolli! ')
                source_elements = sourcelink_value.split('§')
                source_elements = [part.strip() for part in source_elements]
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, source_elements[0]),
                    value=source_elements[0],
                    name='§ ' + source_elements[1]
                ))

            elif 'EKSPERT' in sourcelink_value:
                name = sourcelink_value.replace('EKSPERT', '').strip().strip('{}')
                source_links.append(data_classes.Sourcelink(
                    sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type(name, 'Ekspert', expert_sources_ids_map),
                    value='Ekspert',
                    name=sourcelink_name if sourcelink_name else ''
                ))
            elif 'DGT' in sourcelink_value:
                name = sourcelink_value.replace('DGT ', '').strip().strip('{}')
                source_links.append(data_classes.Sourcelink(
                    sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type(name, 'DGT', expert_sources_ids_map),
                    value='DGT',
                    name=''
                ))
            elif 'PÄRING' in sourcelink_value:
                name = sourcelink_value.replace('PÄRING ', '').strip().strip('{}')
                source_links.append(data_classes.Sourcelink(
                    sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type(name, 'Päring', expert_sources_ids_map),
                    value='Päring',
                    name=''
                ))
            else:
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, sourcelink_value),
                    value=sourcelink_value,
                    name=sourcelink_name if sourcelink_name else ''
                ))


            if type == 'word':
                lexeme_notes.append(data_classes.Lexemenote(
                    value=note_value,
                    lang='est',
                    publicity=True,
                    sourceLinks=source_links
                ))
            elif type == 'concept':
                concept_notes.append(data_classes.Note(
                    value=note_value,
                    lang='est',
                    publicity=True,
                    sourceLinks=source_links
                ))
            else:
                print('error 3')

    # Case #3 :: (source) :: date
    elif '.' in note_raw[-7:-1] or '/' in note_raw[-6:-1]:
        print('Case #3: ' + note_raw)

        # Case #3/1 :: SÜNONÜÜM: T1001 tõlkes; st ühenduse asutus [VEL] {ATM 06.09.1999}. - ok
        if '] {' in note_raw:
            print('Case #3/1: ' + note_raw)
            parts = note_raw.rsplit('] {', 1)
            note_and_sourcelink = parts[0]
            date_with_letters = parts[1]

            # Extract the date without letters.
            date_without_letters = re.sub(r'[A-Za-zöäüõÖÄÜÕ]', '', date_with_letters).strip().replace(' &', '')

            # Extract the note part and the sourcelink value.
            note_parts = note_and_sourcelink.split('[', 1)
            note = note_parts[0].strip()
            sourcelink_value = note_parts[1].rsplit('}', 1)[0].strip()

            corrected_note_value = f'{note} {{{date_without_letters}}}'

            terminologist = re.search(r'{([^{}]+)}\s*$', note_raw)

            if terminologist:
                terminologist = terminologist.group(1)
                parts = terminologist.split()
                term_name = parts[0] if parts else ''

                key = (term_name.strip(), "Eesti Õiguskeele Keskuse terminoloog")
                source_id = term_sources_to_ids_map.get(key)

                source_links.append(data_classes.Sourcelink(
                    sourceId=source_id,
                    value=term_name.strip(),
                    name=''
                ))

            if "EKSPERT" in sourcelink_value:
                name = sourcelink_value.replace("EKSPERT ", '')
                name = name.strip('{}')
                source_links.append(data_classes.Sourcelink(
                    sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type(name, 'Ekspert',
                                                                                          expert_sources_ids_map),
                    value='Ekspert',
                    name=''
                ))
            else:
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, sourcelink_value),
                    value=sourcelink_value,
                    name=''
                ))
            if type == 'word':

                lexeme_notes.append(data_classes.Lexemenote(
                    value=corrected_note_value.strip('.').strip('}')+'}',
                    lang='est',
                    publicity=True,
                    sourceLinks=source_links
                ))
            elif type == 'concept':
                concept_notes.append(data_classes.Note(
                    value=corrected_note_value.strip('.').strip('}')+'}',
                    lang='est',
                    publicity=True,
                    sourceLinks=source_links
                ))
            else:
                print('error 4')

        # Case #3/2 :: broadcasting - the process of transmitting a radio or television signal via an antenna
        # to multiple receivers which can simultaneously pick up the signal [IATE] [{MVS}27.08.2015] - ok
        elif '] [' in note_raw:
            print('Case #3/2: ' + note_raw)
            if note_raw.count(']') > 2:
                parts = note_raw.rsplit('] [', 1)
                lexeme_note = parts[0].strip() + ']'
                date = '[' + parts[1]
                source = ''
                last_bracket_index = lexeme_note.rfind('[')
                if last_bracket_index != -1:
                    closing_bracket_index = lexeme_note.find(']', last_bracket_index)
                    if closing_bracket_index != -1:
                        source = lexeme_note[last_bracket_index + 1:closing_bracket_index].strip()

                lexeme_note = lexeme_note.replace('[' + source + ']', '').strip()
            else:
                first_split = note_raw.split(' [')
                lexeme_note = first_split[0].strip()
                rest_of_string = ' [' + ' ['.join(first_split[1:])

                matches = list(re.finditer(r'\[', rest_of_string))
                second_bracket_index = matches[1].start() if len(matches) > 1 else None

                source = rest_of_string[:second_bracket_index].strip()
                source = source.strip('[]').strip()

                date = rest_of_string[second_bracket_index:].strip()

            term_initials = re.sub(r'[^a-zA-ZöäüõÖÄÜÕ]', '', date)

            date_without_letters = re.sub(r'[z-zA-ZöäüõÖÄÜÕ\s]', '', date).strip().replace('{}', '')

            if term_initials:

                key = (term_initials, "Eesti Õiguskeele Keskuse terminoloog")
                source_id = term_sources_to_ids_map.get(key)

                source_links.append(data_classes.Sourcelink(
                    sourceId=source_id,
                    value=term_initials,
                    name=''
                ))

            if 'EKSPERT' in source:
                name = source.replace('EKSPERT', '').strip().strip('{}')
                source_links.append(data_classes.Sourcelink(
                    sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type(name, 'Ekspert',
                                                                                          expert_sources_ids_map),
                    value='Ekspert',
                    name=''
                ))
            else:
                if "MER, " in source:
                    source_links.append(data_classes.Sourcelink(
                        sourceId=find_source_by_name(name_to_id_map, 'MER'),
                        value='MER',
                        name=source.replace('MER, ', '')
                    ))
                elif ";" in source:
                    print('; in source!')
                    sources = source.split(';')
                    sources = [part.strip() for part in sources]
                    for source in sources:
                        source_links.append(data_classes.Sourcelink(
                            sourceId=find_source_by_name(name_to_id_map, source),
                            value=source,
                            name=''
                        ))
                else:
                    source_links.append(data_classes.Sourcelink(
                        sourceId=find_source_by_name(name_to_id_map, source),
                        value=source,
                        name=''
                    ))
            if type == 'word':
                lexeme_notes.append(data_classes.Lexemenote(
                    value=lexeme_note + ' ' + date_without_letters.strip(),
                    lang='est',
                    publicity=True,
                    sourceLinks=source_links
                ))
            elif type == 'concept':
                concept_notes.append(data_classes.Note(
                    value=lexeme_note + ' ' + date_without_letters.strip(),
                    lang='est',
                    publicity=True,
                    sourceLinks=source_links
                ))
            else:
                print('error 6')

        # Case #3/3 :: date :: 62016CC0158 esineb tõlkega "senine ametikoht". [{KJN}16.10.2019]
        elif note_raw.strip('.').endswith(']'):
            print('Case #3/3: ' + note_raw)

            lexeme_note_without_dot = note_raw.strip('.')

            parts = lexeme_note_without_dot.split('[')
            note = parts[0]
            date_with_letters = parts[1]

            term_initials = date_with_letters.strip('{')[:4].strip('}')

            date_without_letters = re.sub(r'[z-zA-ZöäüõÖÄÜÕ]', '', date_with_letters).strip().replace('{}', '')

            key = (term_initials.strip(), "Eesti Õiguskeele Keskuse terminoloog")
            source_id = term_sources_to_ids_map.get(key)
            source_links.append(data_classes.Sourcelink(
                sourceId=source_id,
                value=term_initials.strip(),
                name=''
            ))

            if type == 'word':

                lexeme_notes.append(data_classes.Lexemenote(
                    value=note + '[' + date_without_letters.strip(),
                    lang='est',
                    publicity=True,
                    sourceLinks=source_links
                ))
            elif type == 'concept':
                concept_notes.append(data_classes.Note(
                    value=note + '[' + date_without_letters.strip(),
                    lang='est',
                    publicity=True,
                    sourceLinks=source_links
                ))
            else:
                print('error 7')

        # Case #3/4 :: date :: "office" kasutatakse kõrgemate ametnike puhul {MRS 26.04.2001}
        elif note_raw.strip('.').endswith('}'):
            print('Case #3/4: ' + note_raw)

            lexeme_note_without_dot = note_raw.strip('.')

            parts = lexeme_note_without_dot.split('{')
            note = parts[0]
            date_with_letters = parts[1]

            date_without_letters = re.sub(r'[z-zA-ZöäüõÖÄÜÕ\s\&]', '', date_with_letters).strip()
            term_initals = date_with_letters.replace(date_without_letters.strip('{}'), '')

            if "&" in term_initals:

                key = (term_initals[:9], "Eesti Õiguskeele Keskuse terminoloog")
                source_id = term_sources_to_ids_map.get(key)
                source_links.append(data_classes.Sourcelink(
                    sourceId=source_id,
                    value=term_initals[:9],
                    name=''
                ))
            elif term_initals.startswith('ATM & MVR'):

                key = ('ATM & MVR', "Eesti Õiguskeele Keskuse terminoloog")
                source_id = term_sources_to_ids_map.get(key)
                source_links.append(data_classes.Sourcelink(
                    sourceId=source_id,
                    value='ATM & MVR',
                    name=''
                ))
            elif term_initals.startswith('MKS, HTM'):

                key = ('MKS, HTM', "Eesti Õiguskeele Keskuse terminoloog")
                source_id = term_sources_to_ids_map.get(key)
                source_links.append(data_classes.Sourcelink(
                    sourceId=source_id,
                    value='MKS, HTM',
                    name=''
                ))
            elif term_initals.startswith('TKK & KMU'):

                key = ('TKK & KMU', "Eesti Õiguskeele Keskuse terminoloog")
                source_id = term_sources_to_ids_map.get(key)
                source_links.append(data_classes.Sourcelink(
                    sourceId=source_id,
                    value='TKK & KMU',
                    name=''
                ))
            elif term_initals.startswith('KNM & KMU'):

                key = ('KNM & KMU', "Eesti Õiguskeele Keskuse terminoloog")
                source_id = term_sources_to_ids_map.get(key)
                source_links.append(data_classes.Sourcelink(
                    sourceId=source_id,
                    value='KNM & KMU',
                    name=''
                ))
            elif term_initals.startswith('LKD & PSK'):

                key = ('LKD & PSK', "Eesti Õiguskeele Keskuse terminoloog")
                source_id = term_sources_to_ids_map.get(key)
                source_links.append(data_classes.Sourcelink(
                    sourceId=source_id,
                    value='LKD & PSK',
                    name=''
                ))
            elif term_initals.startswith('IPU & KMU'):

                key = ('IPU & KMU', "Eesti Õiguskeele Keskuse terminoloog")
                source_id = term_sources_to_ids_map.get(key)
                source_links.append(data_classes.Sourcelink(
                    sourceId=source_id,
                    value='IPU & KMU',
                    name=''
                ))
            elif term_initals.startswith('HTM, RJS, KMR'):

                key = ('HTM, RJS, KMR', "Eesti Õiguskeele Keskuse terminoloog")
                source_id = term_sources_to_ids_map.get(key)
                source_links.append(data_classes.Sourcelink(
                    sourceId=source_id,
                    value='HTM, RJS, KMR',
                    name=''
                ))
            elif term_initals.startswith('AJK, MKS & HTM'):

                key = ('AJK, MKS & HTM', "Eesti Õiguskeele Keskuse terminoloog")
                source_id = term_sources_to_ids_map.get(key)
                source_links.append(data_classes.Sourcelink(
                    sourceId=source_id,
                    value='AJK, MKS & HTM',
                    name=''
                ))
            elif term_initals.startswith('MKK, MKS & HTM'):
                source_links.append(data_classes.Sourcelink(
                    sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type('Terminoloog', 'Terminoloog',
                                                                                          expert_sources_ids_map),
                    value='Terminoloog',
                    name='MKK, MKS & HTM'
                ))
            elif term_initals.startswith('EVA, EEU & HTM'):

                key = ('EVA, EEU & HTM', "Eesti Õiguskeele Keskuse terminoloog")
                source_id = term_sources_to_ids_map.get(key)
                source_links.append(data_classes.Sourcelink(
                    sourceId=source_id,
                    value='EVA, EEU & HTM',
                    name=''
                ))
            else:
                if len(term_initals) >= 4:
                    if term_initals[3] != ' ':
                        if type == 'word':
                            lexeme_notes.append(data_classes.Lexemenote(
                                value='KONTROLLIDA 1: ' + note_raw,
                                lang='est',
                                publicity=False,
                                sourceLinks=source_links
                            ))
                        elif type == 'concept':
                            concept_notes.append(data_classes.Note(
                                value='KONTROLLIDA 2: ' + note_raw,
                                lang='est',
                                publicity=False,
                                sourceLinks=source_links
                            ))
                    else:

                        key = (term_initals[:3], "Eesti Õiguskeele Keskuse terminoloog")
                        source_id = term_sources_to_ids_map.get(key)
                        source_links.append(data_classes.Sourcelink(
                            sourceId=source_id,
                            value=term_initals[:3],
                            name=''
                        ))
                else:
                    term_initals = term_initals[:3]

                    key = (term_initals, "Eesti Õiguskeele Keskuse terminoloog")
                    source_id = term_sources_to_ids_map.get(key)
                    source_links.append(data_classes.Sourcelink(
                        sourceId=source_id,
                        value=term_initals,
                        name=''
                    ))
            if type == 'word':
                lexeme_notes.append(data_classes.Lexemenote(
                    value=note + '{' + date_without_letters.strip(),
                    lang='est',
                    publicity=True,
                    sourceLinks=source_links
                ))
            elif type == 'concept':
                concept_notes.append(data_classes.Note(
                    value=note + '{' + date_without_letters.strip(),
                    lang='est',
                    publicity=True,
                    sourceLinks=source_links
                ))
            else:
                print('error 8')
        else:
            logger.info(f'Unexpected value for lexeme note: {note_raw}')

    # Case #4 :: specific source in the end :: lexeme note goes here [ÕS-2013]
    else:
        print('Case #4: ' + note_raw)

        end_strings = ['ÕS-2013', 'VSL-2012', 'RIIGIKAITSE-2014', 'T1140', 'T1088', 'X1028', 'X40040',
                       '31997L0081', 'EMN-2014', 'X1050', 'T1143', 'T0049', 'ÕS-2006', '32012R0965',
                       'T2050', 'T0060', '32017D0695', 'T1009', 'T30141', 'EKSR-2019', 'T40135', 'T1436',
                       'T2098', 'T40464', 'ÕS-2018', 'RHK-10', 'ICD-10', '32009L0138', 'ICAO-AN17', 'ICAO-AN18',
                       'ICAO-AN10', 'ICAO 4444', 'ICAO 9859', '32012R0923', 'EKK-2007', 'COED12', 'T70911',
                       'ÕS-2018', '32012R0231', 'V00018', 'T50156', 'ICAO-9713', 'T40790', 'X30042', 'COED12',
                       'T40279', 'EKIÜS-2021', 'T30119', 'ICTG-2018', 'MAN-2004', 'X30044', '32004R0785',
                       '32010L0013', 'T1533', 'X30071', '32006L0131', '32006D0257', '32014R0405', 'ODLE-2015',
                       'EKIÜS-2020', '52015DC0599', 'T30063', 'X1060', '32008R0440', '1553', '31975L0442', 'T50143',
                       'T61500', '32016L0798', 'X1057', 'WPG-1637', 'T2050', 'ESA 95', 'VIM-2012', 'EKN, 2710 00 51 00',
                       'T2050', 'T2009', '32009L0003', 'WPG-1581', '32002D0657'
                       ]
        match_found = False

        for end_str in end_strings:
            if note_raw.endswith(f'[{end_str}]'):
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, end_str),
                    value=end_str,
                    name=''
                ))
                if type == 'word':
                    lexeme_notes.append(data_classes.Lexemenote(
                        value=note_raw.replace(f' [{end_str}]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                    match_found = True
                elif type == 'concept':
                    concept_notes.append(data_classes.Note(
                        value=note_raw.replace(f' [{end_str}]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                    match_found = True
                else:
                    print('error 9')
                break

        if not match_found:
            parts = note_raw.rsplit('[', 1)
            if len(parts) > 1 and parts[1].rstrip(']').isdigit():
                sourcelink_part = parts[1].rstrip(']')
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, sourcelink_part),
                    value=sourcelink_part,
                    name=''
                ))
                if type == 'word':
                    lexeme_notes.append(data_classes.Lexemenote(
                        value=parts[0].strip(),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                elif type == 'concept':
                    concept_notes.append(data_classes.Note(
                        value=parts[0].strip(),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                else:
                    print('error 9')
            elif note_raw.endswith('[ÕS-2013; EKSS; VSL-2012]'):
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'ÕS-2013'),
                    value='ÕS-2013',
                    name=''
                ))
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'EKSS'),
                    value='EKSS',
                    name=''
                ))
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'VSL-2012'),
                    value='VSL-2012',
                    name=''
                ))
                if type == 'word':
                    lexeme_notes.append(data_classes.Lexemenote(
                        value=note_raw.replace(' [ÕS-2013; EKSS; VSL-2012]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                elif type == 'concept':
                    concept_notes.append(data_classes.Note(
                        value=note_raw.replace(' [ÕS-2013; EKSS; VSL-2012]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                else:
                    print('error 10')
            elif note_raw.endswith('[EKSS; VSL-2012]'):
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'EKSS'),
                    value='EKSS',
                    name=''
                ))
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'VSL-2012'),
                    value='VSL-2012',
                    name=''
                ))
                if type == 'word':
                    lexeme_notes.append(data_classes.Lexemenote(
                        value=note_raw.replace(' [EKSS; VSL-2012]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                elif type == 'concept':
                    concept_notes.append(data_classes.Note(
                        value=note_raw.replace(' [EKSS; VSL-2012]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                else:
                    print('error 11')
            elif note_raw.endswith('[3656 lk 228]'):
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, '3656'),
                    value='3656',
                    name='228'
                ))
                if type == 'word':
                    lexeme_notes.append(data_classes.Lexemenote(
                        value=note_raw.replace(' [3656 lk 228]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                elif type == 'concept':
                    concept_notes.append(data_classes.Note(
                        value=note_raw.replace(' [3656 lk 228]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                else:
                    print('error 12')
            elif note_raw.endswith('[90786; 90788]'):
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, '90786'),
                    value='90786',
                    name=''
                ))
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, '90788'),
                    value='90788',
                    name=''
                ))
                if type == 'word':
                    lexeme_notes.append(data_classes.Lexemenote(
                        value=note_raw.replace(' [90786; 90788]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                elif type == 'concept':
                    concept_notes.append(data_classes.Note(
                        value=note_raw.replace(' [90786; 90788]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                else:
                    print('error 13')
            elif note_raw.endswith('[M-W; COED12]'):
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'M-W'),
                    value='M-W',
                    name=''
                ))
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'COED12'),
                    value='COED12',
                    name=''
                ))
                if type == 'word':
                    lexeme_notes.append(data_classes.Lexemenote(
                        value=note_raw.replace(' [M-W; COED12]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                elif type == 'concept':
                    concept_notes.append(data_classes.Note(
                        value=note_raw.replace(' [M-W; COED12]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                else:
                    print('error 14')
            elif note_raw.endswith('[ICAO-AN2/10/44; 32012R0923]'):
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'ICAO-AN2/10/44'),
                    value='ICAO-AN2/10/44',
                    name=''
                ))
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, '32012R0923'),
                    value='32012R0923',
                    name=''
                ))
                if type == 'word':
                    lexeme_notes.append(data_classes.Lexemenote(
                        value=note_raw.replace(' [ICAO-AN2/10/44; 32012R0923]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                elif type == 'concept':
                    concept_notes.append(data_classes.Note(
                        value=note_raw.replace(' [ICAO-AN2/10/44; 32012R0923]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                else:
                    print('error 15')
            elif note_raw.endswith('[COO; 89534]'):
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'COO'),
                    value='COO',
                    name=''
                ))
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, '89534'),
                    value='89534',
                    name=''
                ))
                if type == 'word':

                    lexeme_notes.append(data_classes.Lexemenote(
                        value=note_raw.replace(' [COO; 89534]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                elif type == 'concept':
                    concept_notes.append(data_classes.Note(
                        value=note_raw.replace(' [COO; 89534]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                else:
                    print('error 16')
            elif note_raw.endswith('[LS-2015/12 § 69]'):
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'LS-2015/12'),
                    value='LS-2015/12',
                    name='§ 69'
                ))
                if type == 'word':

                    lexeme_notes.append(data_classes.Lexemenote(
                        value=note_raw.replace(' [LS-2015/12 § 69]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                elif type == 'concept':
                    concept_notes.append(data_classes.Note(
                        value=note_raw.replace(' [LS-2015/12 § 69]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                else:
                    print('error 17')
            elif note_raw.endswith('[MKNK; 89823]'):
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'MKNK'),
                    value='MKNK',
                    name=''
                ))
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, '89823'),
                    value='89823',
                    name=''
                ))
                if type == 'word':

                    lexeme_notes.append(data_classes.Lexemenote(
                        value=note_raw.replace(' [MKNK; 89823]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                elif type == 'concept':
                    concept_notes.append(data_classes.Note(
                        value=note_raw.replace(' [MKNK; 89823]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                else:
                    print('error 18')
            elif 'GG019-177' in note_raw:
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'GG019'),
                    value='GG019',
                    name='177'
                ))
                if type == 'word':

                    lexeme_notes.append(data_classes.Lexemenote(
                        value=note_raw.replace(' [GG019-177]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                elif type == 'concept':
                    concept_notes.append(data_classes.Note(
                        value=note_raw.replace(' [GG019-177]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                else:
                    print('error 19')
            elif 'GG019, 241' in note_raw:
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'GG019'),
                    value='GG019',
                    name='241'
                ))
                if type == 'word':

                    lexeme_notes.append(data_classes.Lexemenote(
                        value=note_raw.replace(' [GG019, 241]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                elif type == 'concept':
                    concept_notes.append(data_classes.Note(
                        value=note_raw.replace(' [GG019, 241]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                else:
                    print('error 20')
            elif 'MAV, 432' in note_raw:
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'MAV'),
                    value='MAV',
                    name='432'
                ))
                if type == 'word':

                    lexeme_notes.append(data_classes.Lexemenote(
                        value=note_raw.replace(' [MAV, 432]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                elif type == 'concept':
                    concept_notes.append(data_classes.Note(
                        value=note_raw.replace(' [MAV, 432]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                else:
                    print('error 21')
            elif 'MAV, 516' in note_raw:
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'MAV'),
                    value='MAV',
                    name='516'
                ))
                if type == 'word':

                    lexeme_notes.append(data_classes.Lexemenote(
                        value=note_raw.replace(' [MAV, 516]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                elif type == 'concept':
                    concept_notes.append(data_classes.Note(
                        value=note_raw.replace(' [MAV, 516]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                else:
                    print('error 22')
            elif 'MAV, 238' in note_raw:
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'MAV'),
                    value='MAV',
                    name='238'
                ))
                if type == 'word':

                    lexeme_notes.append(data_classes.Lexemenote(
                        value=note_raw.replace(' [MAV, 238]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                elif type == 'concept':
                    concept_notes.append(data_classes.Note(
                        value=note_raw.replace(' [MAV, 238]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                else:
                    print('error 23')
            elif 'Keelenõuvakk, 2005' in note_raw:
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'Keelenõuvakk, 2005'),
                    value='Keelenõuvakk, 2005',
                    name=''
                ))
                if type == 'word':

                    lexeme_notes.append(data_classes.Lexemenote(
                        value=note_raw.replace(' [Keelenõuvakk, 2005]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                elif type == 'concept':
                    concept_notes.append(data_classes.Note(
                        value=note_raw.replace(' [Keelenõuvakk, 2005]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                else:
                    print('error 24')
            elif '1936, 201' in note_raw:
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, '1936'),
                    value='1936',
                    name='201'
                ))
                if type == 'word':

                    lexeme_notes.append(data_classes.Lexemenote(
                        value=note_raw.replace(' [1936, 201]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                elif type == 'concept':
                    concept_notes.append(data_classes.Note(
                        value=note_raw.replace(' [1936, 201]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                else:
                    print('error 25')
            elif '2211, 143' in note_raw:
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, '2211'),
                    value='2211',
                    name='143'
                ))
                if type == 'word':

                    lexeme_notes.append(data_classes.Lexemenote(
                        value=note_raw.replace(' [2211, 143]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                elif type == 'concept':
                    concept_notes.append(data_classes.Note(
                        value=note_raw.replace(' [2211, 143]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                else:
                    print('error 26')
            elif '9496, lk 85' in note_raw:
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, '9496'),
                    value='9496',
                    name='85'
                ))
                if type == 'word':

                    lexeme_notes.append(data_classes.Lexemenote(
                        value=note_raw.replace(' [9496, lk 85]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                elif type == 'concept':
                    concept_notes.append(data_classes.Note(
                        value=note_raw.replace(' [9496, lk 85]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                else:
                    print('error 27')
            elif '7752 15' in note_raw:
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, '7752'),
                    value='7752',
                    name='15'
                ))
                if type == 'word':

                    lexeme_notes.append(data_classes.Lexemenote(
                        value=note_raw.replace(' [7752 15]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                elif type == 'concept':
                    concept_notes.append(data_classes.Note(
                        value=note_raw.replace(' [7752 15]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                else:
                    print('error 28')
            elif 'LS-2020/12/15 § 2-64' in note_raw:
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'LS-2020/12/15'),
                    value='LS-2020/12/15',
                    name='§ 2-64'
                ))
                if type == 'word':

                    lexeme_notes.append(data_classes.Lexemenote(
                        value=note_raw.replace(' [LS-2020/12/15 § 2-64]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                elif type == 'concept':
                    concept_notes.append(data_classes.Note(
                        value=note_raw.replace(' [LS-2020/12/15 § 2-64]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                else:
                    print('error 29')
            else:
                if type == 'word':
                    lexeme_notes.append(data_classes.Lexemenote(
                        value=note_raw,
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                elif type == 'concept':
                    concept_notes.append(data_classes.Note(
                        value=note_raw,
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                else:
                    print('error 30')

    return lexeme_notes, concept_notes