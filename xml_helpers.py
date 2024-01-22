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
    # Kui keelenditüüp on 'sünonüüm', tuleb Ekilexis väärtusolekuks
    # salvestada 'mööndav'.
    elif descrip_text == 'sünonüüm':
        code = 'mööndav'
    # Kui keelenditüüp on 'variant', siis Ekilexis väärtusolekut ega keelenditüüpi ei salvestata.
    elif descrip_text == 'variant':
        code = None
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

    notes_to_move = {}

    for word in words:
        for lexemeNote in word.lexemeNotes[:]:
            for prefix, state_code in prefix_to_state_code.items():
                if lexemeNote.value.startswith(prefix):
                    cleaned_note = lexemeNote.value.replace(prefix, "", 1)
                    lexemeNote.value = cleaned_note

                    key = (state_code, word.lang)
                    if key not in notes_to_move:
                        notes_to_move[key] = []

                    notes_to_move[key].append(lexemeNote)
                    word.lexemeNotes.remove(lexemeNote)
                    logger.debug('Removed note from word: %s', word.valuePrese)

    for word in words:
        key = (word.lexemeValueStateCode, word.lang)
        if key in notes_to_move:
            word.lexemeNotes.extend(notes_to_move[key])
            logger.debug('Added note to word: %s', word.valuePrese)

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

    full_text = ''.join(element.itertext())
    usage_value, source_info = full_text.split('[', 1) if '[' in full_text else (full_text, '')
    usage_value = usage_value.strip()
    source_info = source_info.strip()
    source_info = source_info.rstrip(']')

    source_value = source_info
    name = ''

    if ';' in source_value:
        parts = source_value.split('; ')
        for part in parts:
            if '§' in part:
                value = re.split(r'§', part, 1)[0].strip()
                name = "§ " + re.split(r'§', part, 1)[1].strip()
                source_links.append(
                    data_classes.Sourcelink(sourceId=find_source_by_name(updated_sources, value),
                                            value=value,
                                            name=name.strip(']')))
            elif 'PÄRING' in part:
                if part == 'PÄRING':
                    source_links.append(
                        data_classes.Sourcelink(
                            sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type('Päring', 'Päring',
                                                                                                  expert_names_to_ids_map),
                            value='Päring',
                            name=''))
                else:
                    expert_name = part.replace('PÄRING ', '')
                    expert_type = 'Päring'
                    source_links.append(
                        data_classes.Sourcelink(
                            sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type(expert_name,
                                                                                                  expert_type,
                                                                                                  expert_names_to_ids_map),
                            value='Päring',
                            name=''))

            elif 'DGT' in part:
                expert_name = part.replace('DGT', '').strip().strip('{}')
                expert_type = 'DGT'

                source_links.append(
                    data_classes.Sourcelink(
                        sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type(expert_name, expert_type,
                                                                                              expert_names_to_ids_map),
                        value='DGT',
                        name=''))

            elif 'PARLAMENT' in part:
                expert_name = part.replace('PARLAMENT', '').strip(' {}')
                expert_type = 'Parlament'

                source_links.append(
                    data_classes.Sourcelink(
                        sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type(expert_name, expert_type,
                                                                                              expert_names_to_ids_map),
                        value='Parlament',
                        name=''))

            elif 'CONSILIUM' in part:
                expert_name = part.replace('CONSILIUM', '').strip(' {}')
                expert_type = 'Consilium'
                source_links.append(
                    data_classes.Sourcelink(
                        sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type(expert_name, expert_type,
                                                                                              expert_names_to_ids_map),
                        value='Consilium',
                        name=''))

            elif 'EKSPERT' in part:

                expert_name = source_info.replace('EKSPERT', '').strip(' {}')
                expert_type = 'Ekspert'
                source_links.append(
                    data_classes.Sourcelink(
                        sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type(expert_name, expert_type,
                                                                                              expert_names_to_ids_map),
                        value='Ekspert',
                        name=''))

            elif ',' in part:
                value = re.split(r',', part, 1)[0].strip()
                name = re.split(r',', part, 1)[1].strip()
                source_links.append(
                    data_classes.Sourcelink(sourceId=find_source_by_name(updated_sources, value),
                                            value=value,
                                            name=name.strip(']')))

            elif part.startswith('EASA NPA 2008-22D. '):
                value = 'EASA NPA 2008-22D'
                source_links.append(
                    data_classes.Sourcelink(sourceId=find_source_by_name(updated_sources, value),
                                            value=value,
                                            name=part.replace('EASA NPA 2008-22D. ', '')))
            elif part.startswith('WP, '):
                source_links.append(
                    data_classes.Sourcelink(sourceId=find_source_by_name(updated_sources, 'WP'),
                                            value='WP',
                                            name=part.replace('WP, ', '')))
            elif part.startswith('BRITANNICA '):
                value = 'BRITANNICA'
                name = part.replace('BRITANNICA ', '')
                source_links.append(
                    data_classes.Sourcelink(sourceId=find_source_by_name(updated_sources, value),
                                            value=value,
                                            name=name.strip(']')))
            elif part.endswith('Finantsinspektsioon'):
                source_links.append(
                    data_classes.Sourcelink(sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type('Finantsinspektsioon', 'Ekspert', expert_names_to_ids_map),
                                            value='Ekspert',
                                            name=''
                                            ))
            elif part.startswith('T40766 '):
                value = 'T40766'
                name = part.replace('T40766 ', '')
                source_links.append(
                    data_classes.Sourcelink(sourceId=find_source_by_name(updated_sources, value),
                                            value=value,
                                            name=name.strip(']')))
            else:
                source_links.append(
                    data_classes.Sourcelink(sourceId=find_source_by_name(updated_sources, part),
                                            value=part,
                                            name=name.strip(']')))
    elif source_value:

        if '§' in source_value:
            value = re.split(r'§', source_value, 1)[0].strip()
            name = "§ " + re.split(r'§', source_value, 1)[1].strip()
            source_links.append(
                data_classes.Sourcelink(sourceId=find_source_by_name(updated_sources, value),
                                        value=value,
                                        name=name.strip(']')))
        elif 'PÄRING' in source_value:
            parts = full_text.strip().split('PÄRING', 1)
            if parts:
                if len(parts[1]) > 1:
                    expert_name = parts[1].strip().strip(']')
                    expert_type = 'Päring'
                    source_links.append(
                        data_classes.Sourcelink(
                            sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type(expert_name,
                                                                                                  expert_type,
                                                                                                  expert_names_to_ids_map),
                            value='Päring',
                            name=''))
                else:
                    source_links.append(
                        data_classes.Sourcelink(
                            sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type('Päring', 'Päring',
                                                                                                  expert_names_to_ids_map),
                            value='Päring',
                            name=''))


        elif 'DGT' in source_value:
            expert_name = source_value.replace('DGT ', '').strip().strip('{}')
            expert_type = 'DGT'

            source_links.append(
                data_classes.Sourcelink(
                    sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type(expert_name, expert_type,
                                                                                          expert_names_to_ids_map),
                    value='DGT',
                    name=''))

        elif 'PARLAMENT' in source_value:
            expert_name = source_value.replace('PARLAMENT ', '').strip(' {}')
            expert_type = 'Parlament'

            source_links.append(
                data_classes.Sourcelink(
                    sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type(expert_name, expert_type,
                                                                                          expert_names_to_ids_map),
                    value='Parlament',
                    name=''))

        elif 'CONSILIUM' in source_value:
            parts = full_text.split('CONSILIUM', 1)
            if parts:
                expert_name = parts[1].strip().strip(']')
                expert_type = 'Consilium'
                source_links.append(
                    data_classes.Sourcelink(
                        sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type(expert_name, expert_type,
                                                                                              expert_names_to_ids_map),
                        value='Consilium',
                        name=''))

        elif 'EKSPERT' in source_value:

            expert_name = source_info.replace('EKSPERT ', '').strip(' {}')
            expert_type = 'Ekspert'
            source_links.append(
                data_classes.Sourcelink(
                    sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type(expert_name, expert_type,
                                                                                          expert_names_to_ids_map),
                    value='Ekspert',
                    name=''))
        elif ',' in source_value:
            value = re.split(r',', source_value, 1)[0].strip()
            name = re.split(r',', source_value, 1)[1].strip()
            source_links.append(
                data_classes.Sourcelink(sourceId=find_source_by_name(updated_sources, value),
                                        value=value,
                                        name=name.strip(']')))
        elif source_value.startswith('EASA NPA 2008-22D. '):
            value = 'EASA NPA 2008-22D'
            source_links.append(
                data_classes.Sourcelink(sourceId=find_source_by_name(updated_sources, value),
                                        value=value,
                                        name=source_value.replace('EASA NPA 2008-22D. ', '')))
        elif source_value.startswith('WP, '):
            source_links.append(
                data_classes.Sourcelink(sourceId=find_source_by_name(updated_sources, 'WP'),
                                        value='WP',
                                        name=source_value.replace('WP, ', '')))
        elif source_value.startswith('BRITANNICA '):
            value = 'BRITANNICA'
            name = source_value.replace('BRITANNICA ', '')
            source_links.append(
                data_classes.Sourcelink(sourceId=find_source_by_name(updated_sources, value),
                                        value=value,
                                        name=name.strip(']')))
        elif source_value.endswith('Finantsinspektsioon'):
            source_links.append(
                data_classes.Sourcelink(sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type('Finantsinspektsioon', 'Ekspert', expert_names_to_ids_map),
                                        value='Ekspert',
                                        name=''
                                        ))
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
    else:
        print('Kontekstil pole viidet: ' + full_text)

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
        "AKE/ALK": "Anna-Liisa Kurve",
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
        "MRS/MST": "Mari Remmelgas/Mari Sutt",
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
        "ÜMT/ÜAU": "Ülle Männart/Ülle Allsalu",
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
        "ELS/ETM": "Eva Lobjakas/Eva Tamm",
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
                    elif name.startswith('IATE, '):
                        source_links_for_definition.append(data_classes.Sourcelink(
                            sourceId=find_source_by_name(name_to_id_map, 'IATE'),
                            value='IATE',
                            name=name.replace('IATE, ', '')
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
                    elif name.startswith('Jane'):
                        source_links_for_definition.append(data_classes.Sourcelink(
                            sourceId=find_source_by_name(name_to_id_map, name),
                            value=name,
                            name=''
                        ))
                    elif name.startswith('ESR, '):
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
    elif sourcelink == 'Greenval Motor Insurance':
        value = 'Greenval Motor Insurance'
        name = ''
    elif sourcelink == 'Glossary-Accident Insurance':
        value = 'Glossary-Accident Insurance'
        name = ''
    elif sourcelink.startswith('American Heritage '):
        value = sourcelink
        name = ''
    elif sourcelink == 'PÄRING':
        value = 'Päring'
        name = ''
        expert_name = 'Päring'
        expert_type = 'Päring'
    elif bool(re.match(r'^X\d{5},', sourcelink)):
        value = sourcelink[:6]
        name = sourcelink.replace(value + ', ', '')
    elif sourcelink == 'CONSILIUM':
        value = 'Consilium'
        name = ''
        expert_name = 'Consilium'
        expert_type = 'Consilium'
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
    elif 'GG005,' in sourcelink:
        value = 'GG005'
        name = sourcelink.replace('GG0005, ', '')
    elif sourcelink.startswith('Harju Elu '):
        value = sourcelink
        name = ''
    elif 'T0057 ' in sourcelink:
        value = 'T0057'
        name = sourcelink.replace('T0057 ', '')
    elif 'T0059 ' in sourcelink:
        value = 'T0059'
        name = sourcelink.replace('T0059 ', '')
    elif 'T0065 ' in sourcelink:
        value = 'T0065'
        name = sourcelink.replace('T0065 ', '')
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
    elif sourcelink.startswith('PakS-2021/05/2 '):
        value = 'PakS-2021/05/2'
        name = sourcelink.replace('PakS-2021/05/2 ', '')
    elif sourcelink.startswith('K80050 '):
        value = 'K80050'
        name = sourcelink.replace('K80050 ', '')
    elif sourcelink.startswith('Ridali '):
        value = sourcelink
        name = ''
    elif '§' in sourcelink:
        value = re.split(r'§', sourcelink, 1)[0].strip()
        name = "§ " + re.split(r'§', sourcelink, 1)[1].strip()
    elif 'ConvRT ' in sourcelink:
        value = 'ConvRT'
        name = sourcelink.replace('ConvRT ', '')
    elif sourcelink.startswith('MRS/MST'):
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
    elif sourcelink == 'MKM 8.03.2011 nr ':
        value = sourcelink
        name = ''
    elif sourcelink.startswith('ICOd '):
        value = sourcelink
        name = ''
    elif sourcelink.startswith('Hacker '):
        value = sourcelink
        name = ''
    elif sourcelink.startswith('EVS-EN 16486:2014. Jäätmematerjalide'):
        value = sourcelink
        name = ''
    elif sourcelink.startswith('BRITANNICA-AC, '):
        value = 'BRITANNICA-AC'
        name = sourcelink.replace('BRITANNICA-AC, ', '')
    elif sourcelink.startswith('TSR, '):
        value = 'TSR'
        name = sourcelink.replace('TSR, ', '')
    elif sourcelink.startswith('ÕS, '):
        value = 'ÕS'
        name = sourcelink.replace('ÕS, ', '')
    elif sourcelink.startswith('96542.'):
        value = '96542'
        name = sourcelink.replace('96542', '')
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
    elif sourcelink == 'EL nõukogu':
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
    elif 'TKP, ' in sourcelink:
        value = 'TKP'
        name = sourcelink.replace('TKP, ', '')
    elif 'T2109 ' in sourcelink:
        value = 'T2109'
        name = sourcelink.replace('T2109 ', '')
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
    lexeme_notes = []
    concept_notes = []
    source_links = []

    # Case #0 :: Whole note is in {} :: {Konsulteeritud Välisministeeriumi tõlkeosakonnaga, KMU 16.11.2001} - OK - 17-11
    if note_raw.startswith('{'):
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
            if ',' in sourcelink_value:
                parts = sourcelink_value.split(", ")
                for part in parts:
                    source_links.append(data_classes.Sourcelink(
                        sourceId=find_source_by_name(name_to_id_map, part),
                        value=part,
                        name=''
                    ))
            elif ';' in sourcelink_value:
                parts = sourcelink_value.split("; ")
                for part in parts:
                    source_links.append(data_classes.Sourcelink(
                        sourceId=find_source_by_name(name_to_id_map, part),
                        value=part,
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

    elif "[AIP-" in note_raw and note_raw.endswith("]"):
        start_index = note_raw.rfind("[")
        if start_index != -1 and "AIP-" in note_raw[start_index:]:
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
                print('error aip')
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
    elif note_raw.endswith("[AC 100-001/03]"):
        source_links.append(data_classes.Sourcelink(
            sourceId=find_source_by_name(name_to_id_map, 'AC 100-001/03'),
            value='AC 100-001/03',
            name=''
        ))

        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw.replace('[AC 100-001/03]', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error yssad')
    elif note_raw.endswith("[MET-juhend; AIP-GEN2.2-2017/06]"):
        source_links.append(data_classes.Sourcelink(
            sourceId=find_source_by_name(name_to_id_map, 'MET-juhend'),
            value='MET-juhend',
            name=''
        ))
        source_links.append(data_classes.Sourcelink(
            sourceId=find_source_by_name(name_to_id_map, 'AIP-GEN2.2-2017/06'),
            value='AIP-GEN2.2-2017/06',
            name=''
        ))
        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw.replace(' [MET-juhend; AIP-GEN2.2-2017/06]', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        elif type == 'concept':
            concept_notes.append(data_classes.Note(
                value=note_raw.replace(' [MET-juhend; AIP-GEN2.2-2017/06]', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error ysad')
    elif note_raw.endswith('[EKSPERT Andres Lipand] {TKK & ELS/ETM 13.10.2000}'):
        key = 'TKK'
        name, source_id = term_sources_to_ids_map.get(key, ("", None))
        source_links.append(data_classes.Sourcelink(
            sourceId=source_id,
            value=name,
            name=''
        ))
        key = 'ELS/ETM'
        name, source_id = term_sources_to_ids_map.get(key, ("", None))
        source_links.append(data_classes.Sourcelink(
            sourceId=source_id,
            value=name,
            name=''
        ))
        source_links.append(
            data_classes.Sourcelink(
                sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type('Andres Lipand', 'Ekspert', expert_sources_ids_map),
                value='Ekspert',
                name=''
            )
        )
        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw.replace('[EKSPERT Andres Lipand] {TKK & ELS/ETM ', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error say')
    elif note_raw.endswith('[EKSPERT Jaan Sootak; EKSPERT Jaan Ginter]'):

        source_links.append(
            data_classes.Sourcelink(
                sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type('Jaan Sootak', 'Ekspert', expert_sources_ids_map),
                value='Ekspert',
                name=''
            )
        )
        source_links.append(
            data_classes.Sourcelink(
                sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type('Jaan Ginter', 'Ekspert', expert_sources_ids_map),
                value='Ekspert',
                name=''
            )
        )
        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw.replace('[EKSPERT Jaan Sootak; EKSPERT Jaan Ginter]', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error say')
    elif note_raw.endswith("{ARU & MLR}"):
        key = 'ARU'
        name, source_id = term_sources_to_ids_map.get(key, ("", None))
        source_links.append(data_classes.Sourcelink(
            sourceId=source_id,
            value=name,
            name=''
        ))
        key = 'MLR'
        name, source_id = term_sources_to_ids_map.get(key, ("", None))
        source_links.append(data_classes.Sourcelink(
            sourceId=source_id,
            value=name,
            name=''
        ))
        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw.replace(' {ARU & MLR}', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error say')
    elif note_raw.endswith("[{ÜMT/ÜAU & ATM} 03.11.1999]"):
        key = 'ÜMT/ÜAU'
        name, source_id = term_sources_to_ids_map.get(key, ("", None))
        source_links.append(data_classes.Sourcelink(
            sourceId=source_id,
            value=name,
            name=''
        ))
        key = 'ATM'
        name, source_id = term_sources_to_ids_map.get(key, ("", None))
        source_links.append(data_classes.Sourcelink(
            sourceId=source_id,
            value=name,
            name=''
        ))
        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw.replace('{ÜMT/ÜAU & ATM} ', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error say')
    elif note_raw.endswith("[{LPK & KMU} 12.11.1999]"):
        key = 'LPK'
        name, source_id = term_sources_to_ids_map.get(key, ("", None))
        source_links.append(data_classes.Sourcelink(
            sourceId=source_id,
            value=name,
            name=''
        ))
        key = 'KMU'
        name, source_id = term_sources_to_ids_map.get(key, ("", None))
        source_links.append(data_classes.Sourcelink(
            sourceId=source_id,
            value=name,
            name=''
        ))
        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw.replace('{LPK & KMU} ', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error say')
    elif note_raw.endswith("{KMR & RRS}"):
        key = 'KMR'
        name, source_id = term_sources_to_ids_map.get(key, ("", None))
        source_links.append(data_classes.Sourcelink(
            sourceId=source_id,
            value=name,
            name=''
        ))
        key = 'RRS'
        name, source_id = term_sources_to_ids_map.get(key, ("", None))
        source_links.append(data_classes.Sourcelink(
            sourceId=source_id,
            value='RRS',
            name=''
        ))
        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw.replace(' {KMR & RRS}', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        elif type == 'concept':
            concept_notes.append(data_classes.Note(
                value=note_raw.replace(' {KMR & RRS}', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error sddy')
    elif note_raw.endswith("{TKK & AJK}"):
        key = 'TKK'
        name, source_id = term_sources_to_ids_map.get(key, ("", None))
        source_links.append(data_classes.Sourcelink(
            sourceId=source_id,
            value=name,
            name=''
        ))
        key = 'AJK'
        name, source_id = term_sources_to_ids_map.get(key, ("", None))
        source_links.append(data_classes.Sourcelink(
            sourceId=source_id,
            value=name,
            name=''
        ))
        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw.replace(' {TKK & AJK}', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error sday')
    elif note_raw.endswith("{RRS & KMR}"):
        key = 'RRS'
        name, source_id = term_sources_to_ids_map.get(key, ("", None))
        source_links.append(data_classes.Sourcelink(
            sourceId=source_id,
            value=name,
            name=''
        ))
        key = 'KMR'
        name, source_id = term_sources_to_ids_map.get(key, ("", None))
        source_links.append(data_classes.Sourcelink(
            sourceId=source_id,
            value=name,
            name=''
        ))
        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw.replace(' {RRS & KMR}', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error sddsday')
    elif note_raw.endswith("{TKK & MLR}"):
        key = 'TKK'
        name, source_id = term_sources_to_ids_map.get(key, ("", None))
        source_links.append(data_classes.Sourcelink(
            sourceId=source_id,
            value=name,
            name=''
        ))
        key = 'MLR'
        name, source_id = term_sources_to_ids_map.get(key, ("", None))
        source_links.append(data_classes.Sourcelink(
            sourceId=source_id,
            value=name,
            name=''
        ))
        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw.replace(' {TKK & MLR}', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error sddsday')
    elif note_raw.endswith("{29.10.1998}"):
        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw,
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error sday')
    elif note_raw.endswith('{Tiina Annus}'):
        source_links.append(data_classes.Sourcelink(
            sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type('Tiina Annus', 'Ekspert',
                                                                                  expert_sources_ids_map),
            value='Ekspert',
            name=''
        ))
        lexeme_notes.append(data_classes.Lexemenote(
            value=note_raw.replace(' {Tiina Annus}', ''),
            lang='est',
            publicity=True,
            sourceLinks=source_links
        ))
    elif note_raw.endswith('{ÕTK juristid}'):
        key = 'ÕTK juristid'
        name, source_id = term_sources_to_ids_map.get(key, ("", None))
        source_links.append(data_classes.Sourcelink(
            sourceId=source_id,
            value='ÕTK juristid',
            name=''
        ))
        lexeme_notes.append(data_classes.Lexemenote(
            value=note_raw.replace(' {ÕTK juristid}', ''),
            lang='est',
            publicity=True,
            sourceLinks=source_links
        ))
    elif note_raw.endswith('{01.09.98}'):
        lexeme_notes.append(data_classes.Lexemenote(
            value=note_raw,
            lang='est',
            publicity=True,
            sourceLinks=source_links
        ))
    elif note_raw.endswith("{EVA}"):
        key = 'EVA'
        name, source_id = term_sources_to_ids_map.get(key, ("", None))
        source_links.append(data_classes.Sourcelink(
            sourceId=source_id,
            value=name,
            name=''
        ))

        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw.replace(' {EVA}', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        elif type == 'concept':
            concept_notes.append(data_classes.Note(
                value=note_raw.replace(' {EVA}', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error y')
    elif note_raw.endswith("{AMS}"):
        key = 'AMS'
        name, source_id = term_sources_to_ids_map.get(key, ("", None))
        source_links.append(data_classes.Sourcelink(
            sourceId=source_id,
            value=name,
            name=''
        ))

        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw.replace(' {AMS}', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        elif type == 'concept':
            concept_notes.append(data_classes.Note(
                value=note_raw.replace(' {AMS}', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error y')
    elif note_raw.endswith("{VZI}"):
        key = 'VZI'
        name, source_id = term_sources_to_ids_map.get(key, ("", None))
        source_links.append(data_classes.Sourcelink(
            sourceId=source_id,
            value=name,
            name=''
        ))

        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw.replace(' {VZI}', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        elif type == 'concept':
            concept_notes.append(data_classes.Note(
                value=note_raw.replace(' {VZI}', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error z')
    elif note_raw.endswith("{ATM & MR}"):
        key = 'ATM'
        name, source_id = term_sources_to_ids_map.get(key, ("", None))
        source_links.append(data_classes.Sourcelink(
            sourceId=source_id,
            value=name,
            name=''
        ))
        key = 'MR'
        name, source_id = term_sources_to_ids_map.get(key, ("", None))
        source_links.append(data_classes.Sourcelink(
            sourceId=source_id,
            value=name,
            name=''
        ))

        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw.replace(' {ATM & MR}', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        elif type == 'concept':
            concept_notes.append(data_classes.Note(
                value=note_raw.replace(' {ATM & MR}', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error zx')
    elif note_raw.endswith("{KNN & KTS}"):
        key = 'KNN'
        name, source_id = term_sources_to_ids_map.get(key, ("", None))
        source_links.append(data_classes.Sourcelink(
            sourceId=source_id,
            value=name,
            name=''
        ))
        key = 'KTS'
        name, source_id = term_sources_to_ids_map.get(key, ("", None))
        source_links.append(data_classes.Sourcelink(
            sourceId=source_id,
            value=name,
            name=''
        ))

        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw.replace(' {KNN & KTS}', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        elif type == 'concept':
            concept_notes.append(data_classes.Note(
                value=note_raw.replace(' {KNN & KTS}', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error zxy')
    elif note_raw.endswith("{MLR & LPK}"):
        key = 'MLR'
        name, source_id = term_sources_to_ids_map.get(key, ("", None))
        source_links.append(data_classes.Sourcelink(
            sourceId=source_id,
            value=name,
            name=''
        ))
        key = 'LPK'
        name, source_id = term_sources_to_ids_map.get(key, ("", None))
        source_links.append(data_classes.Sourcelink(
            sourceId=source_id,
            value=name,
            name=''
        ))

        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw.replace(' {MLR & LPK}', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        elif type == 'concept':
            concept_notes.append(data_classes.Note(
                value=note_raw.replace(' {MLR & LPK}', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error zdxy')

    elif note_raw.endswith("[LPK & MLR]"):
        key = 'LPK'
        name, source_id = term_sources_to_ids_map.get(key, ("", None))
        source_links.append(data_classes.Sourcelink(
            sourceId=source_id,
            value=name,
            name=''
        ))
        key = 'MLR'
        name, source_id = term_sources_to_ids_map.get(key, ("", None))
        source_links.append(data_classes.Sourcelink(
            sourceId=source_id,
            value=name,
            name=''
        ))

        if type == 'concept':
            concept_notes.append(data_classes.Note(
                value=note_raw.replace(' {LPK & MLR}', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error zdxy')
    elif note_raw.endswith('[{ÜMT/ÜAU}06.02.2001] [{MVS}27.11.2018]'):
        key = 'ÜMT/ÜAU'
        name, source_id = term_sources_to_ids_map.get(key, ("", None))
        source_links.append(data_classes.Sourcelink(
            sourceId=source_id,
            value=name,
            name=''
        ))
        key = 'MVS'
        name, source_id = term_sources_to_ids_map.get(key, ("", None))
        source_links.append(data_classes.Sourcelink(
            sourceId=source_id,
            value=name,
            name=''
        ))
        if type == 'word':
            note = note_raw.replace('{ÜMT/ÜAU}', '')
            note = note.replace('{MVS}', '')
            lexeme_notes.append(data_classes.Lexemenote(
                value=note,
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error zdxy')
    elif note_raw.endswith('[PÄRING]'):
        source_links.append(data_classes.Sourcelink(
            sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type('Päring', 'Päring', expert_sources_ids_map),
            value='Päring',
            name=''
        ))

        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw.replace(' [PÄRING]]', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        elif type == 'concept':
            concept_notes.append(data_classes.Note(
                value=note_raw.replace(' [PÄRING]]', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error zdddxy')
    elif note_raw.endswith('[EKSPERT]'):
        source_links.append(data_classes.Sourcelink(
            sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type('Ekspert', 'Ekspert', expert_sources_ids_map),
            value='Ekspert',
            name=''
        ))

        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw.replace(' [EKSPERT]]', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        elif type == 'concept':
            concept_notes.append(data_classes.Note(
                value=note_raw.replace(' [EKSPERT]]', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error zddddxy')

    elif note_raw.endswith('[4053 ISDN]'):
        source_links.append(data_classes.Sourcelink(
            sourceId=find_source_by_name(name_to_id_map, '4053'),
            value='4053',
            name='ISDN'
        ))

        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw.replace('[4053 ISDN]', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error yssead')
    elif note_raw.endswith('[7458 9.4]'):
        source_links.append(data_classes.Sourcelink(
            sourceId=find_source_by_name(name_to_id_map, '7458'),
            value='7458',
            name='9.4'
        ))

        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw.replace('[7458 9.4]', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error yssead')
    elif note_raw.endswith('[SKY Monopulse Secondary Surveillance Radar (MSSR)]'):
        source_links.append(data_classes.Sourcelink(
            sourceId=find_source_by_name(name_to_id_map, 'SKY'),
            value='SKY',
            name='Monopulse Secondary Surveillance Radar (MSSR)'
        ))

        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw.replace('[SKY Monopulse Secondary Surveillance Radar (MSSR)]', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error yssead')
    elif note_raw.endswith('[ZABMW tõlge]'):
        source_links.append(data_classes.Sourcelink(
            sourceId=find_source_by_name(name_to_id_map, 'ZABMW'),
            value='ZABMW',
            name='tõlge'
        ))

        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw.replace('[ZABMW tõlge]', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error yssedsfad')
    elif note_raw.endswith('[ZABMW перевод]'):
        source_links.append(data_classes.Sourcelink(
            sourceId=find_source_by_name(name_to_id_map, 'ZABMW'),
            value='ZABMW',
            name='перевод'
        ))

        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw.replace('[ZABMW перевод]', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error yssedsfad')
    elif note_raw.endswith('[X2060 2.1]'):
        source_links.append(data_classes.Sourcelink(
            sourceId=find_source_by_name(name_to_id_map, 'X2060'),
            value='X2060',
            name='2.1'
        ))

        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw.replace('[X2060 2.1]', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error yssead')
    elif note_raw.endswith('[PH0580 1.2]'):
        source_links.append(data_classes.Sourcelink(
            sourceId=find_source_by_name(name_to_id_map, 'PH0580'),
            value='PH0580',
            name='1.2'
        ))

        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw.replace('[PH0580 1.2]', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error yssead')
    elif note_raw.endswith('[2208 deficit]'):
        source_links.append(data_classes.Sourcelink(
            sourceId=find_source_by_name(name_to_id_map, '2208'),
            value='2208',
            name='deficit'
        ))

        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw.replace('[2208 deficit]', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error yssead')
    elif note_raw.endswith('[TTD folded yarn]'):
        source_links.append(data_classes.Sourcelink(
            sourceId=find_source_by_name(name_to_id_map, 'TTD'),
            value='TTD',
            name='folded yarn'
        ))

        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw.replace('[TTD folded yarn]', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error yssead')
    elif note_raw.endswith('[T30239 1.2]'):
        source_links.append(data_classes.Sourcelink(
            sourceId=find_source_by_name(name_to_id_map, 'T30239'),
            value='T30239',
            name='1.2'
        ))

        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw.replace('[T30239 1.2]', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error yssead')
    elif note_raw.endswith('[NWE Fig]'):
        source_links.append(data_classes.Sourcelink(
            sourceId=find_source_by_name(name_to_id_map, 'NWE'),
            value='NWE',
            name='Fig'
        ))

        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw.replace('[NWE Fig]', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error yssead')
    elif note_raw.endswith('[T61134 1.4]'):
        source_links.append(data_classes.Sourcelink(
            sourceId=find_source_by_name(name_to_id_map, 'T61134'),
            value='T61134',
            name='1.4'
        ))

        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw.replace('[T61134 1.4]', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error yssead')
    elif note_raw.endswith('[OCW pupitre]'):
        source_links.append(data_classes.Sourcelink(
            sourceId=find_source_by_name(name_to_id_map, 'OCW'),
            value='OCW',
            name='pupitre'
        ))

        if type == 'word':
            lexeme_notes.append(data_classes.Lexemenote(
                value=note_raw.replace('[OCW pupitre]', ''),
                lang='est',
                publicity=True,
                sourceLinks=source_links
            ))
        else:
            print('error yssead')

    # Case #2 :: no date :: source ::
    # "Nii Eesti kui ka ELi uutes kindlustusvaldkonna õigusaktides kasutatakse terminit kindlustusandja. [KTTG]" - ok
    elif not note_raw.strip('.')[-3:-1].isdigit():
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

            key = source
            name, source_id = term_sources_to_ids_map.get(key, ("", None))
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
                            key = match.group(1).strip()
                            name, source_id = term_sources_to_ids_map.get(key, ("", None))
                            source_links.append(data_classes.Sourcelink(
                                sourceId=source_id,
                                value=name,
                                name=''
                            ))
                        note_value = note_value + ' [' + source.replace(match.group(1), '').strip() + ']'
                    else:
                        source_links.append(data_classes.Sourcelink(
                            sourceId=find_source_by_name(name_to_id_map, source.strip()),
                            value=source.strip(),
                            name=''
                        ))
            elif '§' in sourcelink_value:
                source_elements = sourcelink_value.split('§')
                source_elements = [part.strip() for part in source_elements]
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, source_elements[0]),
                    value=source_elements[0],
                    name='§ ' + source_elements[1]
                ))
            elif 'ConvRT ' in sourcelink_value:
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'ConvRT'),
                    value='ConvRT',
                    name=sourcelink_value.replace('ConvRT ', '')
                ))
            elif '91946 ' in sourcelink_value:
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, '91946'),
                    value='91946',
                    name=sourcelink_value.replace('91946 ', '')
                ))
            elif 'MDBW ' in sourcelink_value:
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'MDBW'),
                    value='MDBW',
                    name=sourcelink_value.replace('MDBW ', '')
                ))
            elif 'TechoDic ' in sourcelink_value:
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'TechoDic'),
                    value='TechoDic',
                    name=sourcelink_value.replace('TechoDic ', '')
                ))
            elif 'EKSPERT' in sourcelink_value:
                name = sourcelink_value.replace('EKSPERT ', '').strip().strip('{}')
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

    elif note_raw.startswith('RS-2011/12-s ebatäpselt sõnastatud. Mõeldud on linna-, '):
        source_links.append(data_classes.Sourcelink(
            sourceId=find_source_by_name(name_to_id_map, 'RS-2011/12'),
            value='RS-2011/12',
            name=''
        ))
        source_links.append(data_classes.Sourcelink(
            sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type('Kristi Kuldma', 'Ekspert', expert_sources_ids_map),
            value='Ekspert',
            name=''
        ))
        key = 'KKA'
        name, source_id = term_sources_to_ids_map.get(key, ("", None))
        source_links.append(data_classes.Sourcelink(
            sourceId=source_id,
            value=name,
            name=''
        ))
        lexeme_notes.append(data_classes.Lexemenote(
            value='RS-2011/12-s ebatäpselt sõnastatud. Mõeldud on linna-, linnalähiliinide või piirkondlikke '
                  '(raudtee reisijateveo) teenuseid. [21.12.2012]',
            lang='est',
            publicity=True,
            sourceLinks=source_links
        ))

    # Case #3 :: (source) :: date
    elif '.' in note_raw[-7:-1] or '/' in note_raw[-6:-1]:

        # Case #3/1 :: SÜNONÜÜM: T1001 tõlkes; st ühenduse asutus [VEL] {ATM 06.09.1999}. - ok
        if '] {' in note_raw:
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

                key = term_name.strip()
                name, source_id = term_sources_to_ids_map.get(key, ("", None))

                source_links.append(data_classes.Sourcelink(
                    sourceId=source_id,
                    value=term_name.strip(),
                    name=''
                ))

            if '§' in sourcelink_value:
                parts = sourcelink_value.split('§')
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, parts[0].strip()),
                    value=parts[0].strip(),
                    name='§ ' + parts[1].strip()
                ))
            elif 'ENE, ' in sourcelink_value:
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'ENE'),
                    value='ENE',
                    name=sourcelink_value.replace('ENE, ', '')
                ))
            elif 'T1382, ' in sourcelink_value:
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'T1382'),
                    value='T1382',
                    name=sourcelink_value.replace('TI382, ', '')
                ))
            elif ';' in sourcelink_value:
                parts = sourcelink_value.split('; ')
                for part in parts:
                    source_links.append(data_classes.Sourcelink(
                        sourceId=find_source_by_name(name_to_id_map, part.strip()),
                        value=part.strip(),
                        name=''
                    ))
            elif "EKSPERT" in sourcelink_value:
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

                key = term_initials
                name, source_id = term_sources_to_ids_map.get(key, ("", None))

                source_links.append(data_classes.Sourcelink(
                    sourceId=source_id,
                    value=name,
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
                elif "KNV " in source:
                    source_links.append(data_classes.Sourcelink(
                        sourceId=find_source_by_name(name_to_id_map, 'KNV'),
                        value='KNV',
                        name=source.replace('KNV ', '')
                    ))
                elif "T61134 " in source:
                    source_links.append(data_classes.Sourcelink(
                        sourceId=find_source_by_name(name_to_id_map, 'T61134'),
                        value='T61134',
                        name=source.replace('T61134 ', '')
                    ))
                elif ";" in source:
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

            lexeme_note_without_dot = note_raw.strip('.')

            parts = lexeme_note_without_dot.split('[')
            note = parts[0]
            date_with_letters = parts[1]

            term_initials = date_with_letters.strip('{')[:4].strip('}')

            date_without_letters = re.sub(r'[z-zA-ZöäüõÖÄÜÕ]', '', date_with_letters).strip().replace('{}', '')

            key = term_initials.strip()
            name, source_id = term_sources_to_ids_map.get(key, ("", None))
            source_links.append(data_classes.Sourcelink(
                sourceId=source_id,
                value=name,
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

            lexeme_note_without_dot = note_raw.strip('.')

            parts = lexeme_note_without_dot.split('{')
            note = parts[0]
            #print(lexeme_note_without_dot)

            date_with_letters = parts[1]
            date_without_letters = re.sub(r'[z-zA-ZöäüõÖÄÜÕ\s\&]', '', date_with_letters).strip()
            term_initals = date_with_letters.replace(date_without_letters.strip('{}'), '')

            if "&" in term_initals:
                term_initals = term_initals.strip('}').strip()

                parts = term_initals.split(' & ')

                for part in parts:
                    key = part
                    name, source_id = term_sources_to_ids_map.get(key, ("", None))
                    source_links.append(data_classes.Sourcelink(
                        sourceId=source_id,
                        value=name,
                        name=''
                    ))
            else:
                if len(term_initals) >= 4:
                    if term_initals[3] != ' ':
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
                        return lexeme_notes, concept_notes
                    else:

                        key = term_initals[:3]
                        name, source_id = term_sources_to_ids_map.get(key, ("", None))
                        source_links.append(data_classes.Sourcelink(
                            sourceId=source_id,
                            value=name,
                            name=''
                        ))
                else:
                    term_initals = term_initals[:3]

                    key = term_initals
                    name, source_id = term_sources_to_ids_map.get(key, ("", None))
                    source_links.append(data_classes.Sourcelink(
                        sourceId=source_id,
                        value=name,
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
                       'T2050', 'T2009', '32009L0003', 'WPG-1581', '32002D0657', 'X30025', 'X1056', 'X30031', 'X30028',
                       'T1088', 'X30063', 'X2045', 'X2020', 'T30058', 'T30423', 'X40003', 'X1062', 'X2037', 'T30230',
                       'X40088', 'T40803', 'T2050', 'T1511', 'T30058', 'T30423', 'T0046', 'T45065', 'U50112', 'U50043',
                       'ISO/IEC 17025:1999', 'T40090', 'VT WS004190', 'T2010', 'T2044', 'T2031', 'X2054', 'X1063',
                       'T2052', 'T0119', 'T1159', 'T30279', 'X2034', 'X2029', 'X2007', 'T30420', 'T45106', 'T1001'
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
            elif note_raw.endswith('[EKSPERT Maret Ots; 9705; 9706]'):
                source_links.append(data_classes.Sourcelink(
                    sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type('Maret Ots', 'Ekspert', expert_sources_ids_map),
                    value='Ekspert',
                    name=''
                ))
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, '9705'),
                    value='9705',
                    name=''
                ))
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, '9706'),
                    value='9706',
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
            elif note_raw.endswith('[X0000 § 70]'):
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'X0000'),
                    value='X0000',
                    name='§ 70'
                ))
                if type == 'concept':
                    concept_notes.append(data_classes.Note(
                        value=note_raw.replace(' [X0000 § 70]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                else:
                    print('error 151')
            elif note_raw.endswith('[X0000 § 56]'):
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'X0000'),
                    value='X0000',
                    name='§ 56'
                ))
                if type == 'concept':
                    concept_notes.append(data_classes.Note(
                        value=note_raw.replace(' [X0000 § 56]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                else:
                    print('error 151')
            elif note_raw.endswith('[X0000 § 95]'):
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'X0000'),
                    value='X0000',
                    name='§ 95'
                ))
                if type == 'concept':
                    concept_notes.append(data_classes.Note(
                        value=note_raw.replace(' [X0000 § 95]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                else:
                    print('error 151')
            elif note_raw.endswith('[X0001 § 70]'):
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'X0001'),
                    value='X0001',
                    name='§ 70'
                ))
                if type == 'concept':
                    concept_notes.append(data_classes.Note(
                        value=note_raw.replace(' [X0001 § 70]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                else:
                    print('error 151')
            elif note_raw.endswith('[2826, 23]'):
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, '2826'),
                    value='2826',
                    name='23'
                ))
                if type == 'concept':
                    concept_notes.append(data_classes.Note(
                        value=note_raw.replace(' [2826, 23]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                else:
                    print('error 151')
            elif note_raw.endswith('{TL001117} [T1001][T2015]'):
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'T1001'),
                    value='T1001',
                    name=''
                ))
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'T2015'),
                    value='T2015',
                    name=''
                ))
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'TL001117'),
                    value='TL001117',
                    name=''
                ))
                if type == 'concept':
                    concept_notes.append(data_classes.Note(
                        value=note_raw.replace('{TL001117} [T1001][T2015]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                else:
                    print('error 151')
            elif note_raw.endswith('[PH0580 1.2]'):
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'PH0580'),
                    value='PH0580',
                    name='1.2'
                ))
                if type == 'word':
                    lexeme_notes.append(data_classes.Lexemenote(
                        value=note_raw.replace(' [PH0580 1.2]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                elif type == 'concept':
                    concept_notes.append(data_classes.Note(
                        value=note_raw.replace(' [PH0580 1.2]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                else:
                    print('error 11x')
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
            elif note_raw.endswith('[CHA; X027]'):
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'CHA'),
                    value='CHA',
                    name=''
                ))
                source_links.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'X2027'),
                    value='X0227',
                    name=''
                ))
                if type == 'word':
                    lexeme_notes.append(data_classes.Lexemenote(
                        value=note_raw.replace(' [CHA; X2027]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                elif type == 'concept':
                    concept_notes.append(data_classes.Note(
                        value=note_raw.replace(' [CHA; X2027]', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=source_links
                    ))
                else:
                    print('error 14x')
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
                print('mis see on: ' + note_raw)

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


def parse_lang_level_note(note_raw, name_to_id_map, expert_names_to_ids_map, term_sources_to_ids_map):
    sourcelinks_to_find_ids_to = []
    sourcelinks = []

    # There is a sourcelink
    if '[' in note_raw:
        if note_raw.count('[') < 2:
            parts = note_raw.split('[')
            note = parts[0]
            source_value = parts[1].replace(']', '')
            # Multiple sourelink values in sourcelink
            if ';' in source_value:
                parts = source_value.split(';')
                for part in parts:
                    sourcelinks_to_find_ids_to.append(part.strip())
            # One sourcelink
            else:
                sourcelinks_to_find_ids_to.append(source_value)
        else:
            if note_raw.endswith('[IATE] [{SES}07.03.2016]'):
                sourcelinks_to_find_ids_to.append('IATE')
                key = 'SES'
                name, source_id = term_sources_to_ids_map.get(key, ("", None))
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=source_id,
                    value=name,
                    name=''
                ))
                note = 'tegemist katusterminiga kõikide veoliikide jaoks [07.03.2016]'
            elif note_raw.endswith('[Vikipeedia] [{MVS}15.02.2017]'):
                sourcelinks_to_find_ids_to.append('Vikipeedia')
                key = 'MVS'
                name, source_id = term_sources_to_ids_map.get(key, ("", None))
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=source_id,
                    value=name,
                    name=''
                ))
                note = 'Selle asutasid 3. mail 1960 alternatiiviks Euroopa Majandusühendusele riigid, ' \
                           'kes viimasesse ei kuulunud. Tänaseks on sellesse organisatsiooni jäänud üksnes neli ' \
                           'liiget – Island, Liechtenstein, Norra ja Šveits. EFTA-ga ühinemise vastu tunnevad ' \
                           'huvi Fääri saared. [15.02.2017]'
            elif note_raw.endswith('[RelvS-2015/03] [{MPO}21.09.2018]'):
                sourcelinks_to_find_ids_to.append('RelvS-2015/03')
                key = 'MPO'
                name, source_id = term_sources_to_ids_map.get(key, ("", None))
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=source_id,
                    value=name,
                    name=''
                ))
                note = 'Varasemas relvaseaduses RelvS-2015/03 oli sõjaväerelv defineeritud kui relv, mis on ' \
                       'põhiliselt ette nähtud Kaitseväele ja Kaitseliidule lahingutegevuseks ning Kaitseväele, ' \
                       'Kaitseliidule ja Kaitseministeeriumi valitsemisalas olevatele asutustele teenistusülesannete ' \
                       'täitmiseks. Omaduste poolest loetakse sõjaväerelvaks ja selle laskemoonaks üksnes käesoleva ' \
                       'seadusega kehtestatud tingimustele vastav eriohtlikkusega tulirelv ja laskemoon. [21.09.2018]'
            elif note_raw.endswith('(Ca[OCl]2∙CaCl2∙Ca[OH]2∙2H2O). [BRITANNICA-AC]'):
                sourcelinks_to_find_ids_to.append('BRITANNICA-AC')
                note = 'Much chlorine is used to sterilize water and wastes, and the substance is employed either ' \
                       'directly or indirectly as a bleaching agent for paper or textiles and ' \
                       'as “bleaching powder” (Ca[OCl]2∙CaCl2∙Ca[OH]2∙2H2O).'
            elif note_raw.endswith('[EKSPERT Heido Ots] [{MVS, SES}16.11.2018]'):
                sourcelinks_to_find_ids_to.append('EKSPERT Heido Ots')
                key = 'MVS'
                name, source_id = term_sources_to_ids_map.get(key, ("", None))
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=source_id,
                    value=name,
                    name=''
                ))
                key = 'SES'
                name, source_id = term_sources_to_ids_map.get(key, ("", None))
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=source_id,
                    value=name,
                    name=''
                ))
                note = 'Poolhaagis on asjatu piirang, "axle system" võib esineda ka täishaagisel ja autol. [16.11.2018]'
            elif note_raw.endswith('[TER-PLUS] [{MVS}05.05.2017]'):
                sourcelinks_to_find_ids_to.append('TER-PLUS')
                key = 'MVS'
                name, source_id = term_sources_to_ids_map.get(key, ("", None))
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=source_id,
                    value=name,
                    name=''
                ))
                note = 'On a terminology record, it is a type of textual support that helps establish the textual ' \
                       'match between languages by stating the delimiting characteristics of a concept. [05.05.2017]'
            elif note_raw.endswith('[EVS-ISO 1087-1:2002] [{MVS}02.03.2017]'):
                sourcelinks_to_find_ids_to.append('EVS-ISO 1087-1:2002')
                key = 'MVS'
                name, source_id = term_sources_to_ids_map.get(key, ("", None))
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=source_id,
                    value=name,
                    name=''
                ))
                note = 'Eesti keeles ei eristata akronüüme hääldusviisi järgi. [02.03.2017]'
            elif note_raw.endswith('[IATE] [{KKA}4.05.2017]'):
                sourcelinks_to_find_ids_to.append('IATE')
                key = 'KKA'
                name, source_id = term_sources_to_ids_map.get(key, ("", None))
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=source_id,
                    value=name,
                    name=''
                ))
                note = ' This is not a rolling Presidency team and should not be confused with the troika. See "troika - kolmik". [4.05.2017]'

            elif note_raw.endswith('[IATE; Vikipeedia] [{MVS}12.06.2017]'):
                sourcelinks_to_find_ids_to.append('IATE')
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'Vikipeedia'),
                    value='Vikipeedia',
                    name=''
                ))
                key = 'MVS'
                name, source_id = term_sources_to_ids_map.get(key, ("", None))
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=source_id,
                    value=name,
                    name=''
                ))
                note = 'See asendati Aafrika Liiduga. [12.06.2017]'
            elif note_raw.endswith(' {KLA 24.11.1999}'):
                key = 'KLA'
                name, source_id = term_sources_to_ids_map.get(key, ("", None))
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=source_id,
                    value=name,
                    name=''
                ))
                note = 'Kaasajastatud tekstis terminit ei esine. {24.11.1999}'
            elif note_raw.endswith('[EKSPERT Kristi Orav] [{MVS}18.01.2021]'):
                sourcelinks_to_find_ids_to.append('EKSPERT Kristi Orav')
                key = 'MVS'
                name, source_id = term_sources_to_ids_map.get(key, ("", None))
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=source_id,
                    value=name,
                    name=''
                ))
                note = 'Amet keskendub liikuvuse parendamisele, et inimesed ja kaubad saaksid võimalikult sujuvalt ' \
                       'liikuda ühe või mitme transpordiliigi ja teenuse abil ühest kohast teise. Transpordiametis ' \
                       'keskendutakse mugavate teenuste ja sihtkohtade kättesaadavuse tagamisele; targemale maa-, ' \
                       'õhuruumi ja veeteede kasutusele ning tervislikumale ja keskkonnasõbralikumale liiklemisele. ' \
                       'Samuti planeeritakse Transpordiametis nutikaid liikuvuse lahendusi ja viiakse ellu ' \
                       'transpordiliikide üleseid poliitikaid ja projekte. [18.01.2021]'
            elif note_raw.endswith('[RHK-10 põhjal] [{MVS}7.01.2022]'):
                sourcelinks_to_find_ids_to.append('RHK-10')
                key = 'MVS'
                name, source_id = term_sources_to_ids_map.get(key, ("", None))
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=source_id,
                    value=name,
                    name=''
                ))
                note = 'RHK-10 (ICD-10) näitab, mis tüüpi infarktiga on tegemist, nt põrnainfarkt, kilpnäärmeinfarkt, ' \
                       'neerupealise infarkt, äge seljaajuinfarkt, äge müokardiinfarkt, peaajuinfarkt, maksainfarkt, ' \
                       'lihase isheemiline infarkt, neeruinfarkt, platsentainfarkt. Lihtsalt "infarkt" ' \
                       'diagnoosina ei esine. [7.01.2022]'
            else:
                print('mingi muu ' + note_raw)

        for source in sourcelinks_to_find_ids_to:
            if source.startswith('EKSPERT'):
                name = source.replace('EKSPERT ', '')
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type(name, 'Ekspert', expert_names_to_ids_map),
                    value='Ekspert',
                    name=''
                ))
            elif source.startswith('PÄRING '):
                name = source.replace('PÄRING ', '')
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type(name, 'Päring', expert_names_to_ids_map),
                    value='Päring',
                    name=''
                ))
            elif source.startswith('{'):
                parts = source.split('}')
                term_name = parts[0].strip('{}').strip()
                note = note + '[' + parts[1] + ']'
                key = term_name
                name, source_id = term_sources_to_ids_map.get(key, ("", None))
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=source_id,
                    value=name,
                    name=''
                ))
            elif source.startswith('88710 '):
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, '88710'),
                    value='88710',
                    name=source.replace('88710 ', '')
                ))
            elif source.startswith('EME '):
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'EME'),
                    value='EME',
                    name=source.replace('EME ', '')
                ))
            elif '§' in source:
                parts = source.split('§')
                value = parts[0].strip()
                name = '§ ' + parts[1].strip()
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, value),
                    value=value,
                    name=name
                ))
            elif 'WIKIPEDIA ' in source:
                value = 'WIKIPEDIA'
                name = source.replace('WIKIPEDIA ', '')
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, value),
                    value=value,
                    name=name
                ))
            elif 'Vikipeedia ' in source:
                value = 'Vikipeedia'
                name = source.replace('Vikipeedia ', '')
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, value),
                    value=value,
                    name=name
                ))
            elif 'ICAO-ENVR-2019 ' in source:
                value = 'ICAO-ENVR-2019'
                name = source.replace('ICAO-ENVR-2019 ', '')
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, value),
                    value=value,
                    name=name
                ))
            elif 'BRITANNICA ' in source:
                value = 'BRITANNICA'
                name = source.replace('BRITANNICA ', '')
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, value),
                    value=value,
                    name=name
                ))
            elif 'PBAZC ' in source:
                value = 'PBAZC'
                name = source.replace('PBAZC ', '')
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, value),
                    value=value,
                    name=name
                ))
            elif '88182 ' in source:
                value = '88182'
                name = source.replace('88182 ', '')
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, value),
                    value=value,
                    name=name
                ))
            elif '88020 ' in source:
                value = '88020'
                name = source.replace('88020 ', '')
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, value),
                    value=value,
                    name=name
                ))
            elif ' 88020' in source:
                value = '88020'
                name = source.replace(' 88020', '')
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, value),
                    value=value,
                    name=name
                ))
            elif 'LOG-S ' in source:
                value = 'LOG-S'
                name = source.replace('LOG-S ', '')
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, value),
                    value=value,
                    name=name
                ))
            elif 'LTK ' in source:
                value = 'LTK'
                name = source.replace('LTK ', '')
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, value),
                    value=value,
                    name=name
                ))
            elif 'ZABMW ' in source:
                value = 'ZABMW'
                name = source.replace('ZABMW ', '')
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, value),
                    value=value,
                    name=name
                ))
            elif source.startswith('EVS-EN 45020:2008'):
                value = 'EVS-EN 45020:2008'
                name = source.replace('EVS-EN 45020:2008', '').strip()
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, value),
                    value=value,
                    name=name
                ))
            elif source.startswith('88200 '):
                value = '88200'
                name = source.replace('88200 ', '')
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, value),
                    value=value,
                    name=name
                ))
            elif source.startswith('88798 '):
                value = '88798'
                name = source.replace('88798 ', '')
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, value),
                    value=value,
                    name=name
                ))
            elif source.startswith('78200 '):
                value = '78200'
                name = source.replace('78200 ', '')
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, value),
                    value=value,
                    name=name
                ))
            elif source.startswith('88894 '):
                value = '88894'
                name = source.replace('88894 ', '')
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, value),
                    value=value,
                    name=name
                ))
            elif source.startswith('KALAPEEDIA '):
                value = 'KALAPEEDIA'
                name = source.replace('KALAPEEDIA ', '')
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, value),
                    value=value,
                    name=name
                ))
            elif source.startswith('EE-online '):
                value = 'EE-online'
                name = source.replace('EE-online ', '')
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, value),
                    value=value,
                    name=name
                ))
            elif source.startswith('8796 '):
                value = '8796'
                name = source.replace('8796 ', '')
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, value),
                    value=value,
                    name=name
                ))
            elif source.startswith('88213 '):
                value = '88213'
                name = source.replace('88213 ', '')
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, value),
                    value=value,
                    name=name
                ))
            elif source.startswith('NWE '):
                value = 'NWE'
                name = source.replace('NWE ', '')
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, value),
                    value=value,
                    name=name
                ))
            elif ' lk ' in source:
                parts = source.split(' lk ')
                value = parts[0]
                name = 'lk ' + parts[1].strip()
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, value),
                    value=value,
                    name=name
                ))
            else:
                value = source
                name = ''
                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, value),
                    value=value,
                    name=name
                ))

            return data_classes.Note(
                value=note,
                lang='est',
                publicity=True,
                sourceLinks=sourcelinks
            )
    # There is not a sourcelink
    else:
        return data_classes.Note(
            value=note_raw,
            lang='est',
            publicity=True,
            sourceLinks=sourcelinks
        )


def parse_context_like_note(usage_raw, name_to_id_map, expert_names_to_ids_map, term_sources_to_ids_map):
    sourcelinks_to_find_ids_to = []
    sourcelinks = []

    usage = usage_raw
    publicity = True

    if usage.startswith('Prokuröride üldkogu: 1) valib kaks ringkonnaprokuratuuri prokuröri '):
        usage = 'KONTROLLIDA: ' + usage_raw
        publicity = False
    elif usage.startswith('Rahandusministeeriumi valitsemisalas on järgmised ametid ja inspektsioonid: 1) ['):
        usage = 'KONTROLLIDA: ' + usage_raw
        publicity = False
    elif usage.startswith('Siseministeeriumi valitsemisalas on järgmised ametid ja inspektsioonid: 1) Kaitsepolitseiamet; 2) ['):
        usage = 'KONTROLLIDA: ' + usage_raw
        publicity = False
    elif usage.startswith('Prokuröride üldkogu: 1) valib kaks ringkonnaprokuratuuri prokuröri ja ühe Riigiprokuratuuri prokuröri prokuröride konkursikomisjoni liikmeks; ['):
        usage = 'KONTROLLIDA: ' + usage_raw
        publicity = False
    elif usage == 'ÕS-2006 ei soovita sõna "siseriiklik" kasutada [ÕS-2006] [KKA 7.06.2012]':
        usage = 'ÕS-2006 ei soovita sõna "siseriiklik" kasutada [7.06.2012]'
        sourcelinks_to_find_ids_to.append('ÕS-2006')
        sourcelinks_to_find_ids_to.append('{KKA}')
    # There is a sourcelink
    elif '[' in usage_raw:
        if usage_raw.count('[') < 2:
            parts = usage_raw.split('[')
            usage = parts[0]
            source_value = parts[1].replace(']', '')

            # Multiple sourelink values in sourcelink
            if ';' in source_value:
                parts = source_value.split(';')
                for part in parts:
                    sourcelinks_to_find_ids_to.append(part.strip())
            # One sourcelink
            else:
                sourcelinks_to_find_ids_to.append(source_value)
        else:
            if usage_raw.startswith('[') and usage_raw.count('[') == 2:
                first = usage_raw.find('[')
                second = usage_raw.find('[', first + 1)
                parts = usage_raw[:second], usage_raw[second:]

                usage = parts[0]
                value_raw = parts[1].replace('[', '').replace(']', '')
                name = ''

                if '§' in value_raw:
                    value = value_raw.split('§')[0].strip()
                    name = value_raw.replace(value, '').strip()
                else:
                    value = value_raw

                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, value),
                    value=value,
                    name=name
                ))

                return data_classes.Usage(
                    value=usage,
                    lang='est',
                    publicity=True,
                    sourceLinks=sourcelinks
                )
            else:
                # Three [] in the end
                pattern_three = r'\s\[(.*?)\]\s\[(.*?)\]\s\[(.*?)\]$'
                pattern_two = r'\s\[(.*?)\]\s\[(.*?)\]$'

                if re.search(pattern_two, usage_raw):
                    match_two = re.search(pattern_two, usage_raw)
                    for m in match_two.groups():
                        sourcelinks_to_find_ids_to.append(m.strip())

                    # Now modify usage outside the loop
                    for m in match_two.groups():
                        usage_raw = usage_raw.replace('[' + m + ']', '')

                    usage = usage_raw.strip()

                else:
                    usage = 'KONTROLLIDA: ' + usage_raw
                    publicity=False

    for source in sourcelinks_to_find_ids_to:
        if source.startswith('EKSPERT '):
            name = source.replace('EKSPERT ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type(name, 'Ekspert', expert_names_to_ids_map),
                value='Ekspert',
                name=''
            ))
        elif source.startswith('PÄRING '):
            name = source.replace('PÄRING ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type(name, 'Päring', expert_names_to_ids_map),
                value='Päring',
                name=''
            ))
        elif source.startswith('{'):
            parts = source.split('}')
            term_name = parts[0].strip('{}').strip()
            usage = usage + '[' + parts[1] + ']'
            key = term_name
            name, source_id = term_sources_to_ids_map.get(key, ("", None))
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=source_id,
                value=name,
                name=''
            ))
        elif source.startswith('X0007'):
            value = 'X0007'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X0010'):
            value = 'X0010'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X0001'):
            value = 'X0001'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X0002'):
            value = 'X0002'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X30026'):
            value = 'X30026'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X1041'):
            value = 'X1041'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X1060'):
            value = 'X1060'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X2013'):
            value = 'X2013'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X2058'):
            value = 'X2058'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X2035'):
            value = 'X2035'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X2053'):
            value = 'X2053'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X2049'):
            value = 'X2049'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X2049'):
            value = 'X2049'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X2056'):
            value = 'X2056'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X30004'):
            value = 'X30004'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X2051'):
            value = 'X2051'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X30023'):
            value = 'X30023'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X30005'):
            value = 'X30005'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X30073'):
            value = 'X30073'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('T60600'):
            value = 'T60600'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('T70294'):
            value = 'T70294'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('T60600'):
            value = 'T60600'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('T60600'):
            value = 'T60600'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X2064'):
            value = 'X2064'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X2063'):
            value = 'X2063'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X2060'):
            value = 'X2060'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X30073'):
            value = 'X30073'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X30050'):
            value = 'X30050'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X30030'):
            value = 'X30030'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X30006'):
            value = 'X30006'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X30073'):
            value = 'X30073'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X2004'):
            value = 'X2004'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X0001'):
            value = 'X0001'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X0010'):
            value = 'X0010'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X1003'):
            value = 'X1003'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('T70284'):
            value = 'T70284'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('K80050'):
            value = 'K80050'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X1045'):
            value = 'X1045'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X0007'):
            value = 'X0007'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source == 'B 737 OM':
            value = source
            name = ''
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X1015'):
            value = 'X1015'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X2013'):
            value = 'X2013'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X2035'):
            value = 'X2035'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X2026'):
            value = 'X2026'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X2061'):
            value = 'X2061'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X2014'):
            value = 'X2014'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X2006'):
            value = 'X2006'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X2065'):
            value = 'X2065'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X0001'):
            value = 'X0001'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X0010'):
            value = 'X0010'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X0007'):
            value = 'X0007'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X2035'):
            value = 'X2035'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X30003'):
            value = 'X30003'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X30038'):
            value = 'X30038'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X2065'):
            value = 'X2065'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('T1130'):
            value = 'T1130'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X30073'):
            value = 'X30073'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X2004'):
            value = 'X2004'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X40070'):
            value = 'X40070'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('77574'):
            value = '77574'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('PART '):
            value = source
            name = ''
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('MKM 8.06.2005 nr 66 '):
            value = 'MKM 8.06.2005 nr 66'
            name = source.replace('MKM 8.06.2005 nr 66 ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('EVS-ISO '):
            value = source
            name = ''
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('FCL '):
            value = source
            name = ''
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('ZABMW'):
            value = 'ZABMW'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('LOG-S '):
            value = 'LOG-S'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('77574 '):
            value = '77574'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X1044'):
            value = 'X1044'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X2004'):
            value = 'X2004'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X2038'):
            value = 'X2038'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X1064'):
            value = 'X1064'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('T61134'):
            value = 'T61134'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('10524'):
            value = '10524'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('Aquatic '):
            value = source
            name = ''
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('EE-online '):
            value = 'EE-online'
            name = source.replace('EE-online ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('ISO '):
            value = source
            name = ''
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source == 'MKM 22.10.2009 nr 103':
            value = source
            name = ''
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source == 'MKM 08.06.2005 nr 66 Lisa 5':
            value = source
            name = ''
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source == 'MKM 8.03.2011 nr 20 lisa 7':
            value = source
            name = ''
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source == 'LLT AS-WWW':
            value = source
            name = ''
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('77574 '):
            value = '77574'
            name = source.replace(value, '').strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('LENNU '):
            value = source
            name = ''
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('JAR-FCL '):
            value = source
            name = ''
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('AC '):
            value = source
            name = ''
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('ICAO '):
            value = source
            name = ''
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('Eesti seitsmes kliimaaruanne'):
            value = 'Eesti seitsmes kliimaaruanne'
            name = source.replace('Eesti seitsmes kliimaaruanne ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('Eesti vajab püsivat ärikeskkonna revolutsiooni'):
            value = 'Eesti vajab püsivat ärikeskkonna revolutsiooni'
            name = source.replace('Eesti vajab püsivat ärikeskkonna revolutsiooni ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('Choosing a Business Model That Will Grow Your Company'):
            value = 'Choosing a Business Model That Will Grow Your Company'
            name = source.replace('Choosing a Business Model That Will Grow Your Company ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('SKY '):
            value = 'SKY'
            name = source.replace('SKY ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('JAR-OPS '):
            value = source
            name = ''
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source == 'MKM 8.03.2011 nr 20':
            value = source
            name = ''
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('T2109'):
            value = 'T2109'
            name = source.replace('T2109 ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X2059'):
            value = 'X2059'
            name = source.replace('X2059 ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X30040'):
            value = 'X30040'
            name = source.replace('X30040 ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X1064'):
            value = 'X1064'
            name = source.replace('X1064 ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X40030'):
            value = 'X40030'
            name = source.replace('X40030 ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('66790'):
            value = '66790'
            name = source.replace('66790 ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('T1134'):
            value = 'T1134'
            name = source.replace('T1134 ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X30007'):
            value = 'X30007'
            name = source.replace('X30007 ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X30027'):
            value = 'X30027'
            name = source.replace('X30027 ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X30025'):
            value = 'X30025'
            name = source.replace('X30025 ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X30024'):
            value = 'X30024'
            name = source.replace('X30024 ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X30044'):
            value = 'X30044'
            name = source.replace('X30044 ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X30057'):
            value = 'X30057'
            name = source.replace('X30057 ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('T30088'):
            value = 'T30088'
            name = source.replace('T30088 ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('T61134'):
            value = 'T61134'
            name = source.replace('T61134 ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X0011'):
            value = 'X0011'
            name = source.replace('X0011', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X30060'):
            value = 'X30060'
            name = source.replace('X30060', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X30064'):
            value = 'X30064'
            name = source.replace('X30064', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X30075'):
            value = 'X30075'
            name = source.replace('X30075', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X40021'):
            value = 'X40021'
            name = source.replace('X40021 ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X30002'):
            value = 'X30002'
            name = source.replace('X30002 ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X30031'):
            value = 'X30031'
            name = source.replace('X30031 ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X30042'):
            value = 'X30042'
            name = source.replace('X30042 ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X30070'):
            value = 'X30070'
            name = source.replace('X30070 ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X2007'):
            value = 'X2007'
            name = source.replace('X2007', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source == 'MKM 21.04.2009 nr 45':
            value = source
            name = ''
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source == 'Kuritegevus Eestis 2010':
            value = source
            name = ''
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X30046'):
            value = 'X30046'
            name = source.replace('X30046', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('GG005,'):
            value = 'GG005'
            name = source.replace('GG005, ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('T1132'):
            value = 'T1132'
            name = source.replace('T1132', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X0003'):
            value = 'X0003'
            name = source.replace('X0003', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('AMS Glossary'):
            value = source
            name = ''
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('SKY '):
            value = 'SKY'
            name = source.replace('SKY ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source == 'MKM 8.06.2005 nr 66':
            value = source
            name = ''
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('EVS-EN 45020:2008 '):
            value = 'EVS-EN 45020:2008'
            name = source.replace('EVS-EN 45020:2008 ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X40018'):
            value = 'X40018'
            name = source.replace('X40018', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X2012'):
            value = 'X2012'
            name = source.replace('X2012', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('T1400'):
            value = 'T1400'
            name = source.replace('T1400', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('T30158'):
            value = 'T30158'
            name = source.replace('T30158', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('X2055'):
            value = 'X2055'
            name = source.replace('X2055', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('MKM 8.03.2011 nr 20 '):
            value = 'MKM 8.03.2011 nr 20'
            name = source.replace('MKM 8.03.2011 nr 20 ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('Harju Elu '):
            value = source
            name = ''
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('Kuritegevus Eestis '):
            value = source
            name = ''
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('1459 '):
            value = '1459'
            name = source.replace('1459 ', '')
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('EVS-EN '):
            value = source
            name = ''
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('SAR '):
            value = source
            name = ''
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif source.startswith('Glossary-Accident '):
            value = source
            name = ''
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif '§' in source:
            parts = source.split('§')
            value = parts[0].strip()
            name = '§ ' + parts[1].strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif ',' in source:
            parts = source.split(',')
            value = parts[0].strip()
            name = parts[1].strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif ' ' in source:
            parts = source.split(' ')
            value = parts[0].strip()
            name = parts[1].strip()
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))
        elif '[https' in source:
            print('https kontekstis')
        else:
            value = source
            name = ''
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=find_source_by_name(name_to_id_map, value),
                value=value,
                name=name
            ))

    # There is not a sourcelink

    return data_classes.Usage(
        value=usage.strip(),
        lang='est',
        publicity=publicity,
        sourceLinks=sourcelinks
    )

def remove_lexeme_value_state_code(words):
    lang_count = {}
    for word in words:
        if word.lang in lang_count:
            lang_count[word.lang] += 1
        else:
            lang_count[word.lang] = 1

    for word in words:
        if word.lexemeValueStateCode == "eelistatud" and lang_count[word.lang] == 2:
            other_word = next((w for w in words if w.lang == word.lang and w != word), None)
            if other_word and 'l' in other_word.wordTypeCodes:
                word.lexemeValueStateCode = None
        elif word.lexemeValueStateCode == 'mööndav':
            word.lexemeValueStateCode = None

    return words


def split_context_to_parts(usage):
    usages = usage.split("2. ", 1)

    if len(usages) == 2 and usages[0].strip().endswith(']'):
        usages[0] = usages[0].strip()
        usages[1] = "2. " + usages[1]
        return usages
    else:
        return [usage]


def does_note_contain_ampersand_in_sourcelink(note_raw):
    pattern = r'\s\[.*\&.*\]'

    regex = re.compile(pattern)

    if regex.search(note_raw):
        return True
    else:
        return False

def handle_ampersand_notes(type_of_note, note_raw, term_sources_to_ids_map):
    lexeme_notes = []
    concept_notes = []
    sourcelinks = []
    date = ''

    parts = note_raw.split('[', 1)

    if len(parts) > 1:
        temp_sourcelinks = re.split(r'(?=\d)', parts[1], maxsplit=1)
        note_value = parts[0]

        if temp_sourcelinks:
            term_initials = temp_sourcelinks[0].replace('{', '').replace('}', '').split('&')
            for initials in term_initials:
                key = initials.strip()
                name, source_id = term_sources_to_ids_map.get(key, ("", None))
                if source_id:
                    sourcelinks.append(data_classes.Sourcelink(
                        sourceId=source_id,
                        value=name,
                        name=''
                    ))

            if len(temp_sourcelinks) > 1:
                date = temp_sourcelinks[1].strip(']')
    else:
        note_value = parts[0]

    final_value = note_value
    if date:
        final_value += '[' + date + ']'

    if type_of_note == 'word':
        lexeme_notes.append(data_classes.Lexemenote(
            value=final_value,
            lang='est',
            publicity=True,
            sourceLinks=sourcelinks
        ))
    else:
        concept_notes.append(data_classes.Note(
            value=final_value,
            lang='est',
            publicity=True,
            sourceLinks=sourcelinks
        ))

    return lexeme_notes, concept_notes

def handle_note_with_double_initials_in_concept_level(note_value,
                                                   term_sources_to_ids_map,
                                                   expert_names_to_ids_map,
                                                   name_to_id_map):

    conceptnotes = []

    if 'ÜMT/ÜAU' in note_value:
        if 'EKSPERT' in note_value:
            parts = note_value.split('[')
            note_without_date = parts[0]

            source_parts = parts[1].split('{')

            expert_name = source_parts[0].replace('EKSPERT ', '').strip()
            expert_name = expert_name.strip(']')
            date = source_parts[1].replace('ÜMT/ÜAU ', '')
            clean_note = note_without_date + '{' + date

            sourcelinks = []
            name, source_id = term_sources_to_ids_map.get('ÜMT/ÜAU', ("", None))
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=source_id,
                value=name,
                name=''
            ))

            sourcelinks.append(data_classes.Sourcelink(
                sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type(expert_name, 'Ekspert',
                                                                                      expert_names_to_ids_map),
                value='Ekspert',
                name=''
            ))
            conceptnotes.append(data_classes.Note(
                value=clean_note,
                lang='est',
                publicity=True,
                sourceLinks=sourcelinks
            ))
        elif '[{ÜMT/ÜAU' in note_value:
            name, source_id = term_sources_to_ids_map.get('ÜMT/ÜAU', ("", None))

            conceptnotes.append(data_classes.Note(
                value=note_value.replace('{ÜMT/ÜAU}', ''),
                lang='est',
                publicity=True,
                sourceLinks=[data_classes.Sourcelink(
                    sourceId=source_id,
                    value=name,
                    name=''
                )]
            ))
        elif '{ÜMT/ÜAU' in note_value:
            if '&' in note_value:
                if 'ÜMT/ÜAU & LKD' in note_value:
                    sourcelinks = []
                    name, source_id = term_sources_to_ids_map.get('ÜMT/ÜAU', ("", None))
                    sourcelinks.append(data_classes.Sourcelink(
                        sourceId=source_id,
                        value=name,
                        name=''
                    )
                    )

                    name, source_id = term_sources_to_ids_map.get('LKD', ("", None))
                    sourcelinks.append(data_classes.Sourcelink(
                        sourceId=source_id,
                        value=name,
                        name=''
                    )
                    )
                    conceptnotes.append(data_classes.Note(
                        value=note_value.replace('ÜMT/ÜAU & LKD ', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=sourcelinks
                    ))
                elif 'ÜMT/ÜAU & LPK' in note_value:
                    sourcelinks = []
                    name, source_id = term_sources_to_ids_map.get('ÜMT/ÜAU', ("", None))
                    sourcelinks.append(data_classes.Sourcelink(
                        sourceId=source_id,
                        value=name,
                        name=''
                    )
                    )

                    name, source_id = term_sources_to_ids_map.get('LPK', ("", None))
                    sourcelinks.append(data_classes.Sourcelink(
                        sourceId=source_id,
                        value=name,
                        name=''
                    )
                    )
                    conceptnotes.append(data_classes.Note(
                        value=note_value.replace('ÜMT/ÜAU & LPK  ', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=sourcelinks
                    ))
            else:
                name, source_id = term_sources_to_ids_map.get('ÜMT/ÜAU', ("", None))

                conceptnotes.append(data_classes.Note(
                    value=note_value.replace('ÜMT/ÜAU ', ''),
                    lang='est',
                    publicity=True,
                    sourceLinks=[data_classes.Sourcelink(
                        sourceId=source_id,
                        value=name,
                        name=''
                    )]
                ))
        elif '[ÜMT/ÜAU' in note_value:
            name, source_id = term_sources_to_ids_map.get('ÜMT/ÜAU', ("", None))

            conceptnotes.append(data_classes.Note(
                value=note_value.replace('ÜMT/ÜAU ', ''),
                lang='est',
                publicity=True,
                sourceLinks=[data_classes.Sourcelink(
                    sourceId=source_id,
                    value=name,
                    name=''
                )]
            ))
        elif '&' in note_value:

            parts = note_value.split('{')

            source_parts = parts[1].split('&')

            sourcelinks = []

            for part in source_parts:
                part = part.strip()

                if '/' in part:
                    name, source_id = term_sources_to_ids_map.get(part[:7], ("", None))
                    sourcelinks.append(
                        data_classes.Sourcelink(
                            sourceId=source_id,
                            value=name,
                            name=''
                        )
                    )
                else:
                    name, source_id = term_sources_to_ids_map.get(part[:3], ("", None))
                    sourcelinks.append(
                        data_classes.Sourcelink(
                            sourceId=source_id,
                            value=name,
                            name=''
                        )
                    )

            date = note_value[-11:]

            conceptnotes.append(data_classes.Note(
                value=parts[0] + '{' + date,
                lang='est',
                publicity=True,
                sourceLinks=sourcelinks
            ))
        else:
            sourcelinks = []
            name, source_id = term_sources_to_ids_map.get('ÜMT/ÜAU', ("", None))
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=source_id,
                value=name,
                name=''
            )
            )
            name, source_id = term_sources_to_ids_map.get('MRS/MST', ("", None))
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=source_id,
                value=name,
                name=''
            )
            )

            conceptnotes.append(data_classes.Note(
                value=note_value.replace('MRS/MST ja ÜMT/ÜAU ', ''),
                lang='est',
                publicity=True,
                sourceLinks=sourcelinks
            ))
    elif 'MRS/MST' in note_value:
        if '&' in note_value:
            parts = note_value.split('&')
            other_part = parts[1]

            other_term_initals = other_part[:4].strip()
            clean_note = note_value.replace('MRS/MST & ' + other_term_initals + ' ', '')

            sourcelinks = []

            name, source_id = term_sources_to_ids_map.get('MRS/MST', ("", None))
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=source_id,
                value=name,
                name=''
            ))

            name, source_id = term_sources_to_ids_map.get(other_term_initals, ("", None))
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=source_id,
                value=name,
                name=''
            ))

            conceptnotes.append(data_classes.Note(
                value=clean_note,
                lang='est',
                publicity=True,
                sourceLinks=sourcelinks
            ))
        elif '[{MRS/MST' in note_value:
            name, source_id = term_sources_to_ids_map.get('MRS/MST', ("", None))

            conceptnotes.append(data_classes.Note(
                value=note_value.replace('{MRS/MST}', ''),
                lang='est',
                publicity=True,
                sourceLinks=[data_classes.Sourcelink(
                    sourceId=source_id,
                    value=name,
                    name=''
                )]
            ))
        elif ' {MRS/MST ' in note_value:
            name, source_id = term_sources_to_ids_map.get('MRS/MST', ("", None))

            conceptnotes.append(data_classes.Note(
                value=note_value.replace('MRS/MST ', ''),
                lang='est',
                publicity=True,
                sourceLinks=[data_classes.Sourcelink(
                    sourceId=source_id,
                    value=name,
                    name=''
                )]
            ))
        else:
            if note_value.endswith('{MRS/MST}'):
                note_value = note_value.replace(' {MRS/MST}', '')
            elif note_value.endswith('[EKSPERT {MRS/MST}]'):
                note_value = note_value.replace(' [EKSPERT {MRS/MST}]', '')
            else:
                note_value = note_value.replace('MRS/MST ', '')

            name, source_id = term_sources_to_ids_map.get('MRS/MST', ("", None))

            conceptnotes.append(data_classes.Note(
                value=note_value,
                lang='est',
                publicity=True,
                sourceLinks=[data_classes.Sourcelink(
                    sourceId=source_id,
                    value=name,
                    name=''
                )]
            ))
    elif 'AKE/ALK' in note_value:
        name, source_id = term_sources_to_ids_map.get('AKE/ALK', ("", None))

        conceptnotes.append(data_classes.Note(
            value=note_value.replace('AKE/ALK ', ''),
            lang='est',
            publicity=True,
            sourceLinks=[data_classes.Sourcelink(
                sourceId=source_id,
                value=name,
                name=''
            )]
        ))
    elif 'ELS/ETM' in note_value:
        if '&' in note_value:

            parts = note_value.split('{')

            source_parts = parts[1].split('&')

            sourcelinks = []

            for part in source_parts:
                part = part.strip()
                if len(part) < 8:
                    name, source_id = term_sources_to_ids_map.get(part, ("", None))
                    sourcelinks.append(
                        data_classes.Sourcelink(
                            sourceId=source_id,
                            value=name,
                            name=''
                        )
                    )
                else:
                    name, source_id = term_sources_to_ids_map.get(part[:3], ("", None))
                    sourcelinks.append(
                        data_classes.Sourcelink(
                            sourceId=source_id,
                            value=name,
                            name=''
                        )
                    )

            date = note_value[11:]

            conceptnotes.append(data_classes.Note(
                value=parts[0] + '{' + date,
                lang='est',
                publicity=True,
                sourceLinks=sourcelinks
            ))
        elif '[{ELS/ETM}' in note_value:
            name, source_id = term_sources_to_ids_map.get('ELS/ETM', ("", None))

            conceptnotes.append(data_classes.Note(
                value=note_value.replace('{ELS/ETM}', ''),
                lang='est',
                publicity=True,
                sourceLinks=[data_classes.Sourcelink(
                    sourceId=source_id,
                    value=name,
                    name=''
                )]
            ))
        elif ' {ELS/ETM ' in note_value:
            name, source_id = term_sources_to_ids_map.get('ELS/ETM', ("", None))

            conceptnotes.append(data_classes.Note(
                value=note_value.replace('ELS/ETM ', ''),
                lang='est',
                publicity=True,
                sourceLinks=[data_classes.Sourcelink(
                    sourceId=source_id,
                    value=name,
                    name=''
                )]
            ))
        elif '[ELS/ETM' in note_value:
            name, source_id = term_sources_to_ids_map.get('ELS/ETM', ("", None))

            conceptnotes.append(data_classes.Note(
                value=note_value.replace('ELS/ETM ', ''),
                lang='est',
                publicity=True,
                sourceLinks=[data_classes.Sourcelink(
                    sourceId=source_id,
                    value=name,
                    name=''
                )]
            ))
        elif '[{ELS/ETM}' in note_value:
            name, source_id = term_sources_to_ids_map.get('ELS/ETM', ("", None))

            conceptnotes.append(data_classes.Note(
                value=note_value.replace('{ELS/ETM}', ''),
                lang='est',
                publicity=True,
                sourceLinks=[data_classes.Sourcelink(
                    sourceId=source_id,
                    value=name,
                    name=''
                )]
            ))
        else:
            print('muu')
    elif 'PTE/PTH' in note_value:
        name, source_id = term_sources_to_ids_map.get('PTE/PTH', ("", None))

        conceptnotes.append(data_classes.Note(
            value=note_value.replace('PTE/PTH ', ''),
            lang='est',
            publicity=True,
            sourceLinks=[data_classes.Sourcelink(
                sourceId=source_id,
                value=name,
                name=''
            )]
        ))
    elif 'IKS/IFH' in note_value:
        name, source_id = term_sources_to_ids_map.get('IKS/IFH', ("", None))

        conceptnotes.append(data_classes.Note(
            value=note_value.replace('IKS/IFH ', ''),
            lang='est',
            publicity=True,
            sourceLinks=[data_classes.Sourcelink(
                sourceId=source_id,
                value=name,
                name=''
            )]
        ))
    return conceptnotes

def handle_note_with_double_initials_in_term_level(lexeme_note_raw,
                                                   term_sources_to_ids_map,
                                                   expert_names_to_ids_map,
                                                   name_to_id_map):
    lexemenotes = []
    lexeme_tags = []

    if 'ÜMT/ÜAU' in lexeme_note_raw:
        if 'EKSPERT' in lexeme_note_raw:
            parts = lexeme_note_raw.split('[')
            date = parts[2].replace('{ÜMT/ÜAU}', '[')
            clean_note = parts[0] + date
            expert_name = parts[1].replace('EKSPERT ', '').strip()
            expert_name = expert_name.strip(']')

            sourcelinks = []
            name, source_id = term_sources_to_ids_map.get('ÜMT/ÜAU', ("", None))
            sourcelinks.append(data_classes.Sourcelink(
                    sourceId=source_id,
                    value=name,
                    name=''
                )
            )

            sourcelinks.append(data_classes.Sourcelink(
                sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type(expert_name, 'Ekspert',
                                                                                      expert_names_to_ids_map),
                value='Ekspert',
                name=''
            ))

            lexemenotes.append(data_classes.Lexemenote(
                value=clean_note,
                lang='est',
                publicity=True,
                sourceLinks=sourcelinks
            ))
        elif 'ÜMT/ÜAU &' in lexeme_note_raw:
            name, source_id = term_sources_to_ids_map.get('AKE/ALK', ("", None))

            lexemenotes.append(data_classes.Lexemenote(
                value=lexeme_note_raw.replace('AKE/ALK ', ''),
                lang='est',
                publicity=True,
                sourceLinks=[data_classes.Sourcelink(
                    sourceId=source_id,
                    value=name,
                    name=''
                )]
            ))
        elif '[{ÜMT/ÜAU' in lexeme_note_raw:

            if '[X0036]' in lexeme_note_raw:

                clean_note = lexeme_note_raw.replace('[X0036] ', '')
                clean_note = clean_note.replace('{ÜMT/ÜAU}', '')

                sourcelinks = []

                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'X0036'),
                    value='X0036',
                    name=''
                ))

                name, source_id = term_sources_to_ids_map.get('ÜMT/ÜAU', ("", None))

                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=source_id,
                    value=name,
                    name=''
                ))

                lexemenotes.append(data_classes.Lexemenote(
                    value=clean_note,
                    lang='est',
                    publicity=True,
                    sourceLinks=sourcelinks
                ))
            elif '[EUR]' in lexeme_note_raw:

                clean_note = lexeme_note_raw.replace('[EUR] ', '')
                clean_note = clean_note.replace('{ÜMT/ÜAU}', '')

                sourcelinks = []

                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=find_source_by_name(name_to_id_map, 'EUR'),
                    value='EUR',
                    name=''
                ))

                name, source_id = term_sources_to_ids_map.get('ÜMT/ÜAU', ("", None))

                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=source_id,
                    value=name,
                    name=''
                ))

                lexemenotes.append(data_classes.Lexemenote(
                    value=clean_note,
                    lang='est',
                    publicity=True,
                    sourceLinks=sourcelinks
                ))
            elif lexeme_note_raw.count('[') > 1:
                lexeme_tags.append('kontrolli ilmikut')
                lexemenotes.append(data_classes.Lexemenote(
                    value=lexeme_note_raw,
                    lang='est',
                    publicity=False,
                    sourceLinks=[]
                ))
            else:
                name, source_id = term_sources_to_ids_map.get('ÜMT/ÜAU', ("", None))

                lexemenotes.append(data_classes.Lexemenote(
                    value=lexeme_note_raw.replace('{ÜMT/ÜAU}', ''),
                    lang='est',
                    publicity=True,
                    sourceLinks=[data_classes.Sourcelink(
                        sourceId=source_id,
                        value=name,
                        name=''
                    )]
                ))

        elif '{ÜMT/ÜAU' in lexeme_note_raw:

            if '[' in lexeme_note_raw:
                if 'X0000' in lexeme_note_raw:

                    clean_note = lexeme_note_raw.replace('[X0000] ', '')
                    clean_note = clean_note.replace('ÜMT/ÜAU ', '')

                    sourcelinks = []

                    sourcelinks.append(data_classes.Sourcelink(
                        sourceId=find_source_by_name(name_to_id_map, 'X0000'),
                        value='X0000',
                        name=''
                    ))

                    name, source_id = term_sources_to_ids_map.get('ÜMT/ÜAU', ("", None))

                    sourcelinks.append(data_classes.Sourcelink(
                        sourceId=source_id,
                        value=name,
                        name=''
                    ))

                    lexemenotes.append(data_classes.Lexemenote(
                        value=clean_note,
                        lang='est',
                        publicity=True,
                        sourceLinks=sourcelinks
                    ))
                elif '[X1006]' in lexeme_note_raw:
                    clean_note = lexeme_note_raw.replace('[X1006] ', '')
                    clean_note = clean_note.replace('ÜMT/ÜAU ', '')

                    sourcelinks = []

                    sourcelinks.append(data_classes.Sourcelink(
                        sourceId=find_source_by_name(name_to_id_map, 'X1006'),
                        value='X1006',
                        name=''
                    ))

                    name, source_id = term_sources_to_ids_map.get('ÜMT/ÜAU', ("", None))

                    sourcelinks.append(data_classes.Sourcelink(
                        sourceId=source_id,
                        value=name,
                        name=''
                    ))

                    lexemenotes.append(data_classes.Lexemenote(
                        value=clean_note,
                        lang='est',
                        publicity=True,
                        sourceLinks=sourcelinks
                    ))
                elif '[X30028]' in lexeme_note_raw:
                    clean_note = lexeme_note_raw.replace('[X30028] ', '')
                    clean_note = clean_note.replace('ÜMT/ÜAU ', '')

                    sourcelinks = []

                    sourcelinks.append(data_classes.Sourcelink(
                        sourceId=find_source_by_name(name_to_id_map, 'X30028'),
                        value='X30028',
                        name=''
                    ))

                    name, source_id = term_sources_to_ids_map.get('ÜMT/ÜAU', ("", None))

                    sourcelinks.append(data_classes.Sourcelink(
                        sourceId=source_id,
                        value=name,
                        name=''
                    ))

                    lexemenotes.append(data_classes.Lexemenote(
                        value=clean_note,
                        lang='est',
                        publicity=True,
                        sourceLinks=sourcelinks
                    ))
                elif '[EUR]' in lexeme_note_raw:
                    clean_note = lexeme_note_raw.replace('[EUR] ', '')
                    clean_note = clean_note.replace('ÜMT/ÜAU ', '')

                    sourcelinks = []

                    sourcelinks.append(data_classes.Sourcelink(
                        sourceId=find_source_by_name(name_to_id_map, 'EUR'),
                        value='EUR',
                        name=''
                    ))

                    name, source_id = term_sources_to_ids_map.get('ÜMT/ÜAU', ("", None))

                    sourcelinks.append(data_classes.Sourcelink(
                        sourceId=source_id,
                        value=name,
                        name=''
                    ))

                    lexemenotes.append(data_classes.Lexemenote(
                        value=clean_note,
                        lang='est',
                        publicity=True,
                        sourceLinks=sourcelinks
                    ))
                elif '[TER]' in lexeme_note_raw:
                    clean_note = lexeme_note_raw.replace('[TER] ', '')
                    clean_note = clean_note.replace('ÜMT/ÜAU ', '')

                    sourcelinks = []

                    sourcelinks.append(data_classes.Sourcelink(
                        sourceId=find_source_by_name(name_to_id_map, 'TER'),
                        value='TER',
                        name=''
                    ))

                    name, source_id = term_sources_to_ids_map.get('ÜMT/ÜAU', ("", None))

                    sourcelinks.append(data_classes.Sourcelink(
                        sourceId=source_id,
                        value=name,
                        name=''
                    ))

                    lexemenotes.append(data_classes.Lexemenote(
                        value=clean_note,
                        lang='est',
                        publicity=True,
                        sourceLinks=sourcelinks
                    ))
                else:
                    name, source_id = term_sources_to_ids_map.get('ÜMT/ÜAU', ("", None))

                    lexemenotes.append(data_classes.Lexemenote(
                        value=lexeme_note_raw.replace('ÜMT/ÜAU ', ''),
                        lang='est',
                        publicity=True,
                        sourceLinks=[data_classes.Sourcelink(
                            sourceId=source_id,
                            value=name,
                            name=''
                        )]
                    ))
            else:
                name, source_id = term_sources_to_ids_map.get('ÜMT/ÜAU', ("", None))

                lexemenotes.append(data_classes.Lexemenote(
                    value=lexeme_note_raw.replace('ÜMT/ÜAU ', ''),
                    lang='est',
                    publicity=True,
                    sourceLinks=[data_classes.Sourcelink(
                        sourceId=source_id,
                        value=name,
                        name=''
                    )]
                ))
        else:
            name, source_id = term_sources_to_ids_map.get('ÜMT/ÜAU', ("", None))

            lexemenotes.append(data_classes.Lexemenote(
                value=lexeme_note_raw.replace('ÜMT/ÜAU ', ''),
                lang='est',
                publicity=True,
                sourceLinks=[data_classes.Sourcelink(
                    sourceId=source_id,
                    value=name,
                    name=''
                )]
            ))
    elif 'AKE/ALK' in lexeme_note_raw:
        name, source_id = term_sources_to_ids_map.get('AKE/ALK', ("", None))

        lexemenotes.append(data_classes.Lexemenote(
            value=lexeme_note_raw.replace('AKE/ALK ', ''),
            lang='est',
            publicity=True,
            sourceLinks=[data_classes.Sourcelink(
                sourceId=source_id,
                value=name,
                name=''
            )]
        ))
    elif 'ELS/ETM' in lexeme_note_raw:
        if 'EKSPERT' in lexeme_note_raw:
            parts = lexeme_note_raw.split('[')
            expert_name = parts[1].replace('EKSPERT', '').strip().replace(']', '').replace('{', '').replace('}', '')
            sourcelinks = []
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=expert_sources_helpers.get_expert_source_id_by_name_and_type(expert_name, 'Ekspert',
                                                                                      expert_names_to_ids_map),
                value='Ekspert',
                name=''
            ))
            name, source_id = term_sources_to_ids_map.get('ELS/ETM', ("", None))
            sourcelinks.append(data_classes.Sourcelink(
                sourceId=source_id,
                value=name,
                name=''
            ))
            lexemenotes.append(data_classes.Lexemenote(
                value=parts[0] + '[' + parts[2].replace('ELS/ETM', ''),
                lang='est',
                publicity=True,
                sourceLinks=sourcelinks
            ))
        else:
            note_value = lexeme_note_raw.replace('ELS/ETM', '').replace('{}', '').replace('{ ', '{').replace('[ ', '[')
            name, source_id = term_sources_to_ids_map.get('ELS/ETM', ("", None))
            lexemenotes.append(data_classes.Lexemenote(
                value=note_value,
                lang='est',
                publicity=True,
                sourceLinks=[data_classes.Sourcelink(
                    sourceId=source_id,
                    value=name,
                    name=''
                )]
            ))
    elif 'MRS/MST' in lexeme_note_raw:
        if lexeme_note_raw.endswith('}'):
            if '&' in lexeme_note_raw:
                parts = lexeme_note_raw.split('{')
                note_part = parts[0]
                other_part = parts[1]

                second_initials_and_date = other_part.split(' ')

                sourcelinks = []

                name, source_id = term_sources_to_ids_map.get(second_initials_and_date[0], ("", None))

                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=source_id,
                    value=name,
                    name=''
                ))

                name, source_id = term_sources_to_ids_map.get(second_initials_and_date[2], ("", None))

                sourcelinks.append(data_classes.Sourcelink(
                    sourceId=source_id,
                    value=name,
                    name=''
                ))

                lexemenotes.append(data_classes.Lexemenote(
                    value=note_part + '{' + second_initials_and_date[3],
                    lang='est',
                    publicity=True,
                    sourceLinks=sourcelinks
                ))

            else:
                name, source_id = term_sources_to_ids_map.get('MRS/MST', ("", None))
                lexemenotes.append(data_classes.Lexemenote(
                    value=lexeme_note_raw.replace('MRS/MST ', ''),
                    lang='est',
                    publicity=True,
                    sourceLinks=[data_classes.Sourcelink(
                        sourceId=source_id,
                        value=name,
                        name=''
                    )]
                ))
        elif lexeme_note_raw.endswith(']'):
            name, source_id = term_sources_to_ids_map.get('MRS/MST', ("", None))

            lexemenotes.append(data_classes.Lexemenote(
                value=lexeme_note_raw.replace('{MRS/MST}', ''),
                lang='est',
                publicity=True,
                sourceLinks=[data_classes.Sourcelink(
                    sourceId=source_id,
                    value=name,
                    name=''
                )]
            ))
        else:
            note_sourcelinks = []
            name, source_id = term_sources_to_ids_map.get('MRS/MST', ("", None))

            note_sourcelinks.append(data_classes.Sourcelink(
                sourceId=source_id,
                value=name,
                name=''
            ))
            name, source_id = term_sources_to_ids_map.get('SES', ("", None))

            note_sourcelinks.append(data_classes.Sourcelink(
                sourceId=source_id,
                value=name,
                name=''
            ))
            lexemenotes.append(data_classes.Lexemenote(
                value="Vaste pärineb Kindlustusinspektsiooni kahjukindlustuse osakonna juhatajalt Priit Kask'ilt {21.11.2000}.",
                lang='est',
                publicity=True,
                sourceLinks=note_sourcelinks
            ))
    elif 'PTE/PTH' in lexeme_note_raw:

        sourcelinks = []

        sourcelinks.append(data_classes.Sourcelink(
            sourceId=find_source_by_name(name_to_id_map, 'T2023'),
            value='T2023',
            name=''
        ))

        name, source_id = term_sources_to_ids_map.get('PTE/PTH', ("", None))

        sourcelinks.append(data_classes.Sourcelink(
            sourceId=source_id,
            value=name,
            name=''
        ))

        lexemenotes.append(data_classes.Lexemenote(
            value="Tõlgitud ka: 'jääkaine' {04.05.1999}",
            lang='est',
            publicity=True,
            sourceLinks=[sourcelinks]
        ))
    elif 'IKS/IFH' in lexeme_note_raw:
        name, source_id = term_sources_to_ids_map.get('IKS/IFH', ("", None))
        lexemenotes.append(data_classes.Lexemenote(
            value=lexeme_note_raw.replace('IKS/IFH ', ''),
            lang='est',
            publicity=True,
            sourceLinks=[data_classes.Sourcelink(
                sourceId=source_id,
                value=name,
                name=''
            )]
        ))

    return lexemenotes, lexeme_tags

def map_concept_type_to_tag_name(concept_type):
    tag_name = ''
    if concept_type == 'termin':
        tag_name = 'term termin'
    elif concept_type == 'ametinimetus':
        tag_name = 'term ametinimetus'
    elif concept_type == 'tõlkeprobleem':
        tag_name =  'term tõlkeprobleem'
    elif concept_type == 'õigusakti pealkiri':
        tag_name = 'term õigusakti pealkiri'
    elif concept_type == 'organisatsioon|asutus':
        tag_name = 'term organisatsioon/asutus'
    elif concept_type == 'dokumendi pealkiri':
        tag_name = 'term dokumendi pealkiri'
    elif concept_type == 'organisatsioon, asutus':
        tag_name = 'term organisatsioon/asutus'
    else:
        return tag_name

    return tag_name