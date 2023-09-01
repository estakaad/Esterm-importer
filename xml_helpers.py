import logging
import xml.etree.ElementTree as ET
import log_config
from langdetect import detect
import re
import data_classes
import json

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


def remove_whitespace_before_numbers(value: str) -> str:
    return re.sub(r'(?<=\S)\s*(\d+[.)])', r' \1', value)


##################################
## Word "Kontekst" > word.usage ##
##################################

# Returns the usage ("Kontekst") value without the source link + sourcelinks
def extract_usage_and_its_sourcelink(element, updated_sources):
    source_links = []
    full_text = ''.join(element.itertext())
    usage_value, source_info = full_text.split('[', 1) if '[' in full_text else (full_text, '')
    usage_value = usage_value.strip()

    source_info = source_info.strip()
    source_info = source_info.rstrip(']')

    xref_element = element.find('.//xref')
    source_name = xref_element.text if xref_element is not None else ''
    source_link_specific = None

    # 'Abiteenistujatele laienevad töölepingu seadus ja muud tööseadused niivõrd,
    # kuivõrd käesoleva seaduse või avalikku teenistust reguleerivate eriseadustega
    # ei sätestata teisiti. [<xref Tlink="Allikas:X0002">X0002</xref> §13-2]'
    if xref_element is not None and xref_element.tail:
        source_link_specific = xref_element.tail.strip()
    # 'Parents who are raising children have the right to assistance from the state. [77184]'
    elif source_info:
        source_name = source_info

    value_for_displaying = (source_name if source_name else '') + ((' ' +
        source_link_specific) if source_link_specific else '')

    source_links.append(
        data_classes.sourceLink(find_source_by_name(updated_sources, source_name), searchValue=source_name,
                                value=value_for_displaying.strip(']')))

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


def edit_note_without_multiple_languages(note):

    sourcelink_searchvalue = ''
    sourcelink_display_value = ''

    # Extract date
    date_pattern = r'[\{\[]\{*\w+\}*\s*\d+[\.\\]\d+[\.\\]\d+[\}\]]$'
    date_match = re.search(date_pattern, note)

    note_without_date = note

    if date_match:
        original_date = date_match.group()
        date = ''.join([char for char in original_date if not char.isalpha() and char != ' '])
        date = date.replace('{}', '')
    else:
        original_date = None
        date = None

    # Remove date from note
    if original_date:
        note_without_date = note_without_date.replace(original_date, '').strip()

    # Extract source
    source_pattern = r'\[.*\]$'
    source_match = re.search(source_pattern, note_without_date)

    if source_match:
        source = source_match.group()
        if 'xref' in source:
            xref_pattern = r'<xref Tlink=".*?">(.*?)</xref>'
            xref_match = re.search(xref_pattern, source)

            # Variable to store the text inside <xref>...</xref>
            inside_xref = None

            if xref_match:
                inside_xref = xref_match.group(1)

            # Extracting the remaining text after </xref>
            remaining_text = source.split('</xref>')[-1].strip()

            if inside_xref == 'EKSPERT':
                sourcelink_searchvalue = remaining_text
                sourcelink_display_value = inside_xref + ' ' + remaining_text.replace(']','')
            else:
                sourcelink_searchvalue = inside_xref
                sourcelink_display_value = inside_xref + ((' ' + remaining_text.replace(']','')) if remaining_text else '')

            last_instance_index = note_without_date.rfind(source)

            if last_instance_index != -1:
                note_without_date = note_without_date[:last_instance_index] + note_without_date[
                                                                              last_instance_index + len(source):]

    note = note_without_date + ((' ' + date) if date else '')

    return note, sourcelink_searchvalue.replace(']',''), sourcelink_display_value
#
# test1 = ''''Olema otsustamisvõimeline' - 'have a quorum' [<xref Tlink="Allikas:X0000">X0000</xref> § 70]'''
# test2 = 'Eesti äriseadustiku tõlkes on ingliskeelses tekstis samuti lühend OÜ. {KMU 22.10.2004}'
# test3 = 'üleminek pärijale-transmission to an heir'
# test4 = 'Välisministeeriumi rahvusvahelise õiguse büroo seisukoht on selline: treaty (dogovor, traité, vertrag) ' \
#         '= leping ja agreement (soglašenije, accord, abkommen) = kokkulepe. ' \
#         '[<xref Tlink="Allikas:EKSPERT">EKSPERT</xref> Peter Pedak]'
# test5 = 'Vaata ka kirjet nr 92159 "Transpordiamet". [{MVS}18.01.2021]'
# test6 = 'Siin on tegemist ametiasutuse nimetusega. Vaata ka kirjet "Kaitsejõudude Peastaap - ' \
#         'General Staff of the Defence Forces". [ÜMT 03.04.1996]'
# test7 = '''1. samm: 'VAT'-i (Eestis: käibemaks) puhul saab eelmistes staadiumides arvestatud
# käibemaksu enda käibelt arvestatud käibemaksust maha arvata, 'turnover tax'i puhul kuhjuvad
# erinevates staadiumides võetavad käibemaksud üksteise otsa.
# [<xref Tlink="Allikas:EKSPERT">EKSPERT</xref> Ain Ulmre, Rahandusministeeriumi käibemaksuspetsialist]
# [{KMU}27.04.1999] Võrdle kirjega 'turnover tax - kumuleeruv käibemaks'.'''
#
# edit_note_without_multiple_languages(test1)
# edit_note_without_multiple_languages(test2)
# edit_note_without_multiple_languages(test3)
# edit_note_without_multiple_languages(test4)
# edit_note_without_multiple_languages(test5)
# edit_note_without_multiple_languages(test6)
# edit_note_without_multiple_languages(test7)


##########################################
## "Definitsioon" > concept.definitions ##
##########################################

# Function for splitting and preserving definition element content
def split_and_preserve_xml(descrip_element):
    elements_and_text = list(descrip_element)
    current_text = ""
    individual_definitions = []
    for item in elements_and_text:
        if ET.iselement(item):
            if re.search(r'\n\d\.', current_text):
                individual_definitions.extend([d.strip() for d in re.split(r'\n\d\.', current_text) if d.strip()])
                current_text = ""

            if individual_definitions:
                individual_definitions[-1] += ET.tostring(item, encoding='unicode')
            else:
                current_text += ET.tostring(item, encoding='unicode')
        else:
            current_text += item.strip()

    if current_text:
        individual_definitions.extend([d.strip() for d in re.split(r'\n\d\.', current_text) if d.strip()])

    return individual_definitions


# Definition contains the definition value and its sourcelink names.
# The sourcelinks manifest themselves in different formats.
# This function splits the definition element to definition value and sourcelink names
# TODO: What if there are multiple sourcelinks?
#  <descrip type="Definitsioon">an instruction that specifies
#  a funds transfer [<xref Tlink="en:EUR">EUR</xref>]
#  [<xref Tlink="Allikas:TERMIUM">TERMIUM</xref>]</descrip>
def check_definition_content(root):

    if root.xpath('xref'):
        text_before_xref = root.xpath('xref/preceding-sibling::text()')
        xref_link_value = root.xpath('xref/text()')
        text_after_xref = root.xpath('xref/following-sibling::text()')
        text_before_xref_str = ''.join(text_before_xref).strip()
    else:
        text_before_xref_str = root.text if root.text else ''
        xref_link_value = None
        text_after_xref = None

    xref_link_value_str = ''.join(xref_link_value).strip() if xref_link_value else None
    text_after_xref_str = ''.join(text_after_xref).strip() if text_after_xref else None

    if '[' in text_before_xref_str and ']' in text_before_xref_str:
        text_before_bracket, text_in_bracket = text_before_xref_str.split('[', 1)
        text_in_bracket = text_in_bracket.split(']', 1)[0]
    else:
        text_before_bracket = text_before_xref_str
        text_in_bracket = None

    if text_before_bracket.endswith('['):
        text_before_bracket = text_before_bracket[:-1].strip()

    if text_before_bracket.startswith('1. '):
        text_before_bracket = text_before_bracket[len('1. '):]

    if text_after_xref_str is not None:
        if ']' in text_after_xref_str:
            text_after_xref_str = ''.join(text_after_xref).replace(']', '').strip() if text_after_xref else ''

    return text_before_bracket, text_in_bracket, xref_link_value_str, text_after_xref_str


# In case definition contains more than one definition, it is split, but this breaks the XML tags.
# This function adds the missing XML tags
def fix_xml_fragments(fragments, tag_name):
    fixed_fragments = []
    for i, fragment in enumerate(fragments):
        if i == 0:
            if not fragment.strip().endswith(f"</{tag_name}>"):
                fragment += f"</{tag_name}>"
        elif i == len(fragments) - 1:
            if not fragment.strip().startswith(f"<{tag_name}"):
                fragment = f"<{tag_name}>" + fragment
        else:
            fragment = f"<{tag_name}>" + fragment + f"</{tag_name}>"

        fixed_fragments.append(fragment)
    return fixed_fragments


# Parse definition, split it to definition value and sourcelink and return the definition object
def create_definition_object(lang, definition_element, updated_sources):
    source_links = []

    text_before_xref_str, text_in_bracket, xref_link_value_str, text_after_xref_str = \
        check_definition_content(definition_element)

    if xref_link_value_str:
        if xref_link_value_str.startswith('EKSPERT {'):
            search_value = xref_link_value_str[9:-1]
            value = 'EKSPERT ' + xref_link_value_str[9:-1] + (' ' + text_after_xref_str if text_after_xref_str else "")
        else:
            search_value = xref_link_value_str
            value = xref_link_value_str + (' ' + text_after_xref_str if text_after_xref_str else "")

        source_links.append(data_classes.sourceLink(
            sourceId=find_source_by_name(updated_sources, xref_link_value_str),
            searchValue=search_value,
            value=value
        ))
    else:
        if text_in_bracket and text_in_bracket.startswith('EKSPERT {'):
            search_value = text_in_bracket[9:-1]
            value = 'EKSPERT ' + text_in_bracket[9:-1]
        else:
            search_value = text_in_bracket
            value = text_in_bracket

        source_links.append(data_classes.sourceLink(
            sourceId=find_source_by_name(updated_sources, text_in_bracket),
            searchValue=search_value,
            value=value
        ))

    return data_classes.Definition(
        value=text_before_xref_str,
        lang=lang,
        sourceLinks=source_links,
        definitionTypeCode='definitsioon')


############################################
## "Allikaviide" > word.lexemesourcelinks ##
############################################

# There can be multiple lexeme source links. Split them to separate sourcelink objects.
def split_lexeme_sourcelinks_to_individual_sourcelinks(root, updated_sources):
    source_links = []

    # Pre-process the root string to replace '][' or '] [' with '];['
    # and also replace ',' (with optional space) with ';'
    root = re.sub(r'\]\s*\[|,\s*', '];[', root)

    # Now split by semicolon, as all source links are now separated by it
    list_of_raw_sourcelinks = root.split(';')

    for item in list_of_raw_sourcelinks:

        item = item.strip()

        # Handle cases where source is an expert
        if "EKSPERT" in item:
            stripped_item = item.replace("[", "").replace("]", "")
            expert_item = stripped_item.replace("{", "").replace("}", "")
            if expert_item.startswith('<xref'):
                xref_match = re.search(r'<xref .*?>(.*?)<\/xref>', expert_item)
                if xref_match:
                    searchValue = expert_item[xref_match.end():].strip()
                    value = xref_match.group(1) + ' '+ expert_item[xref_match.end():].strip()
                    source_link = data_classes.sourceLink(sourceId=0, searchValue=searchValue, value=value)
                else:
                    logger.warning('EKSPERT in lexeme sourcelinks, but failed to extract the value.')
            else:
                source_link = data_classes.sourceLink(sourceId=0, searchValue=expert_item.replace("EKSPERT ", "", 1), value=expert_item)

        # [<xref Tlink="Allikas:X0010K4">X0010K4</xref> 6-4] or <xref Tlink="Allikas:HOS-2015/12/37">HOS-2015/12/37</xref>
        elif item.startswith('<xref') or (item.startswith('[') and item.endswith(']')):
            if item.startswith('[') and item.endswith(']'):
                item = item[1:-1]

            xref_match = re.search(r'<xref .*?>(.*?)<\/xref>', item)
            if xref_match:
                searchValue = xref_match.group(1)
                value = item[xref_match.end():].strip()
                source_link = data_classes.sourceLink(sourceId=0, searchValue=searchValue.strip('[]'), value=value)
            else:
                searchValue = item
                value = item
                source_link = data_classes.sourceLink(sourceId=0, searchValue=searchValue.strip('[]'), value=value)
                continue
        else:
            try:
                # <xref Tlink="Allikas:TER-PLUS">TER-PLUS</xref>
                item_element = ET.fromstring(item)
                searchValue = item_element.text
                value = item_element.tail if item_element.tail else ""
            except ET.ParseError:
                # If it's not XML, treat it as a valid string
                # ÕL
                # PS-2015/05
                searchValue = item
                value = ""

            value = value.strip()
            source_link = data_classes.sourceLink(
                sourceId=find_source_by_name(updated_sources, searchValue),
                searchValue=searchValue.strip('[]'),
                value=value)

        source_links.append(source_link)

    return source_links


######################################
## word "Märkus" > word.lexemeNotes ##
######################################

# If there is a date in the end of the lexeme note and before it the initials of a person,
# then remove the initials, but keep the date.
# If there is a sourcelink in the brackets in the end of the lexeme note, extract it. If it contains
# of the main value and its tail, then separate them.
def extract_lexeme_note_and_its_sourcelinks(string):
    # Define a pattern to match square brackets and their contents
    # at the end of the string
    pattern_for_finding_content_in_brackets = r'(.*)\[(.*?)\]$'

    date_string = ''
    source = ''
    tail = ''
    text_before_bracket = string

    matches = re.findall(pattern_for_finding_content_in_brackets, string)

    if matches:
        text_before_bracket, bracket_content = matches[0]

        # Extracting initials and date
        pattern_for_initials_and_date = r'\[{?\w*}?\s?(\d+\.\d+\.\d+)\]'
        initials_and_date_matches = re.findall(pattern_for_initials_and_date, '[' + bracket_content + ']')

        if initials_and_date_matches:
            date_string = initials_and_date_matches[0]
            pattern_for_source_before_initials = r'\[(.*?)\]\s*\[{?\w*}?\s?\d+\.\d+\.\d+\]'
            source_matches = re.findall(pattern_for_source_before_initials, string)
            if source_matches:
                source = source_matches[0]
        else:
            # Check if brackets contain xref
            pattern_for_matching_xref = r'<xref Tlink="Allikas:(.*?)">(.*?)<\/xref>(?:\s*(.*?))?\s*$'
            xref_matches = re.findall(pattern_for_matching_xref, bracket_content)
            if xref_matches:
                source, _, tail = xref_matches[0]
                tail = tail if tail else None
            else:
                # If there is not a xref element in the brackets, the source is the string in the brackets
                source = bracket_content

    if source:
        pattern_to_remove = r'\[' + re.escape(source) + r'\]\s*$'
        text_before_bracket = re.sub(pattern_to_remove, '', text_before_bracket).rstrip()

    if date_string:
        text_before_bracket = text_before_bracket + ' [' + date_string + ']'

    text_before_bracket = text_before_bracket.replace('  ', ' ')

    if source.startswith('EKSPERT '):
        source = source.replace("{", "").replace("}", "")

    if tail.startswith('EKSPERT '):
        source = tail.replace("{", "").replace("}", "")

    return text_before_bracket, date_string, source, tail


######################################
## Sources ##
######################################

# Preprocess sources with ID-s, because otherwise it will take forever to find the match between name and ID
# Not sure if there are duplicate names, but just in case there are, let's map the name to a list of matching ID-s
def create_name_to_id_mapping(sources):
    name_to_ids = {}
    for source in sources:
        source_id = source['id']
        logger.info(f"Processing source ID: {source_id}")  # Debug line
        for prop in source['sourceProperties']:
            prop_type = prop['type']
            prop_value = prop['valueText']
            logger.info(f"  Prop type: {prop_type}, Prop value: {prop_value}")  # Debug line
            if prop_type == 'SOURCE_NAME':
                name = prop_value
                if name in name_to_ids:
                    name_to_ids[name].append(source_id)
                else:
                    name_to_ids[name] = [source_id]

    return name_to_ids


# Return ID if there is exactly one match. Return None, if there are 0 matches or more than one matches.
def find_source_by_name(name_to_ids_map, name):
    source_ids = name_to_ids_map.get(name)

    if source_ids is None:
        print(name)
        logger.warning(f"Warning: Source ID for '{name}' not found.")
        return None

    if len(source_ids) == 1:
        logger.info(f"Source ID for '{name}' is {source_ids[0]}")
        return source_ids[0]
    else:
        logger.warning(f"Warning: Duplicate entries found for '{name}'.")
        return None


# Remove sourceLink objects if sourceId is 0.
def remove_source_links_with_zero_id(json_data):
    for concept in json_data:
        for section in ['definitions', 'notes', 'words']:
            for item in concept.get(section, []):
                filtered_source_links = [source_link for source_link in item.get('sourceLinks', []) if
                                         source_link.get('sourceId') != 0]
                item['sourceLinks'] = filtered_source_links

                if section == 'words':
                    filtered_lexeme_source_links = [source_link for source_link in item.get('lexemeSourceLinks', []) if
                                                    source_link.get('sourceId') != 0]
                    item['lexemeSourceLinks'] = filtered_lexeme_source_links

    return json_data