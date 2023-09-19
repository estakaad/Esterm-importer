from datetime import datetime
from lxml import etree
import json
import xml_helpers
import os
import data_classes
import log_config
import re
from lxml.etree import tostring

logger = log_config.get_logger()


# Parse the whole Esterm XML and return aviation concepts, all other concepts and the sources of the concepts
def parse_mtf(root, name_to_id_map):
    concepts = []
    aviation_concepts = []

    # For testing #
    counter = 1

    for conceptGrp in root.xpath('/mtf/conceptGrp'):
        # # # # # For testing
        if counter % 2000 == 0:
           logger.info(f'counter: {counter}')
           break

        counter += 1
        # End

        concept = data_classes.Concept(datasetCode='estermtest',
                                       manualEventOn=None,
                                       manualEventBy=None,
                                       firstCreateEventOn=None,
                                       firstCreateEventBy=None)
        logger.info("Started parsing concept.")

        type_of_concept = xml_helpers.type_of_concept(conceptGrp)

        # Only continue parsing if the concept is actually a concept. Skip sources and domains.
        if type_of_concept == 'source':
            logger.debug('Concept is actually a source. Skipping it.')
            continue
        elif type_of_concept == 'domain':
            logger.debug('Concept is acutally a domain. Skipping it.')
            continue
        elif type_of_concept == 'aviation':
            list_to_append = aviation_concepts
            logger.debug('Concept will be added to the list of aviation concepts.')
        elif type_of_concept == 'general':
            list_to_append = concepts
            logger.debug('Concept will be added to the general list of concepts.')
        else:
            list_to_append = concepts
            logger.debug('Concept will be added to the general list of concepts.')

        # Get concept ID
        concept_id = conceptGrp.find('concept').text
        concept.conceptIds.append(concept_id)
        logger.info(f'Added concept ID {concept_id}')

        # Get origination date
        origination_transac_grp_element = conceptGrp.find(".//transacGrp/transac[@type='origination']/..")
        modification_transac_grp_element = conceptGrp.find(".//transacGrp/transac[@type='modification']/..")

        if origination_transac_grp_element is not None:
            origination_date_element = origination_transac_grp_element.find("date")
            if origination_date_element is not None:
                origination_date = origination_date_element.text
                origination_date_object = datetime.strptime(origination_date, "%Y-%m-%dT%H:%M:%S")
                concept.firstCreateEventOn = origination_date_object.strftime('%d.%m.%Y')
                transac_element = origination_transac_grp_element.find("transac")
                if transac_element is not None:
                    concept.firstCreateEventBy = xml_helpers.map_initials_to_names(transac_element.text)
                    # if concept.firstCreateEventBy is None:
                    #     print(transac_element.text)

        if modification_transac_grp_element is not None:
            modification_date_element = modification_transac_grp_element.find("date")
            if modification_date_element is not None:
                modification_date = modification_date_element.text
                modification_date_object = datetime.strptime(modification_date, "%Y-%m-%dT%H:%M:%S")
                concept.manualEventOn = modification_date_object.strftime('%d.%m.%Y')
                transac_element = modification_transac_grp_element.find("transac")
                if transac_element is not None:
                    concept.manualEventBy = xml_helpers.map_initials_to_names(transac_element.text)
                    # if concept.manualEventBy is None:
                    #     print(transac_element.text)

        # Parse concept level descrip elements and add their values as attributes to Concept
        for descrip_element in conceptGrp.xpath('descripGrp/descrip'):

            descrip_element_value = etree.tostring(descrip_element, encoding='unicode', method='text')

            # Get concept domain and add to the list of concept domains
            if descrip_element.get('type') == 'Valdkonnaviide':
                for domain in descrip_element_value.split(';'):
                    domain = domain.strip()
                    if domain:
                        concept.domains.append(data_classes.Domain(code=domain, origin='lenoch'))

            # Get concept notes and add to the list of concept notes.
            elif descrip_element.get('type') == 'Märkus':
                raw_note_value = xml_helpers.get_description_value(descrip_element)
                note_value = None

                if xml_helpers.does_note_contain_multiple_languages(raw_note_value):
                    note_value = xml_helpers.edit_note_with_multiple_languages(raw_note_value)
                else:
                    note, value, name, expert_note = xml_helpers.edit_note_without_multiple_languages(raw_note_value)

                if note_value:
                    concept.notes.append(data_classes.Note(
                        value=note_value,
                        lang='est',
                        publicity=True
                    ))
                else:
                    if expert_note:
                        if expert_note.value is not None:
                            concept.notes.append(expert_note)
                            logger.debug('Added concept expert note: %s', expert_note)
                    if value:
                        source_links = []

                        source_links.append(
                            data_classes.Sourcelink(
                                sourceId=xml_helpers.find_source_by_name(name_to_id_map, value),
                                value=value,
                                name=name
                            )
                        )
                        concept.notes.append(data_classes.Note(
                            value=note,
                            lang='est',
                            publicity=True,
                            sourceLinks=source_links
                        ))
                    else:
                        concept.notes.append(data_classes.Note(
                            value=note,
                            lang='est',
                            publicity=True
                        ))


                logger.debug('Added concept note: %s', descrip_element_value)

            # Get concept tööleht and add its value to concept forum list.
            elif descrip_element.get('type') == 'Tööleht':

                worksheet = descrip_element_value.replace("\n", "").replace("\t", "")

                concept.forums.append(data_classes.Forum(
                    value='Tööleht: ' + worksheet)
                )

                if descrip_element_value:
                    logger.debug('Added tööleht to forums: %s', descrip_element_value.replace("\n", "").replace("\t", ""))

            elif descrip_element.get('type') == 'Sisemärkus':
                forum_note = re.sub(r"\{.*?\}", "", descrip_element_value)
                forum_note = re.sub(r"]\n*\t*$", "]", forum_note)
                forum_note = forum_note.strip()

                concept.forums.append(data_classes.Forum(
                    value=forum_note
                ))
                if descrip_element_value:
                    logger.debug('Added sisemärkus to forums: %s', forum_note)


        logger.info('Added concept domains: %s', str(concept.domains))
        if concept.notes:
            logger.info('Added concept notes: %s', str(concept.notes))
        if concept.forums:
            logger.info('Added concept forum: %s', str(concept.forums))

        # Concept level data is parsed, now to parsing word (term) level data
        words, definitions, concept_notes = parse_words(conceptGrp, name_to_id_map)

        for word in words:
            concept.words.append(word)

        for definition in definitions:
            concept.definitions.append(definition)

        for note in concept_notes:
            concept.notes.append(note)

        list_to_append.append(concept)
        logger.info('Finished parsing concept.')

    return concepts, aviation_concepts


# Parse word elements in one concept in XML
def parse_words(conceptGrp, name_to_id_map):

    words = []
    definitions = []
    notes_for_concept = []
    is_public = xml_helpers.are_terms_public(conceptGrp)
    logger.debug('Is concept public? %s', is_public)

    for languageGrp in conceptGrp.xpath('languageGrp'):

        # Handle definitions which are on the languageGrp level, not on the termGrp level
        for descripGrp in languageGrp.xpath('descripGrp[descrip/@type="Definitsioon"]'):

            lang_grp = languageGrp.xpath('language')[0].get('lang')
            logger.debug('Definition language: %s', lang_grp)
            lang_grp = xml_helpers.match_language(lang_grp)
            logger.debug(('Definition language after matching: %s', lang_grp))

            definition = descripGrp.find('./descrip')
            #
            # semicolon_in_brackets = r'\s\[.*;.*\]$'
            # links_in_brackets = r'.*\[.*\]\s\[.*\]$'
            #
            # print(''.join(descripGrp.itertext()))
            #
            # if re.search(semicolon_in_brackets, ''.join(descripGrp.itertext())):
            #     print('test semico: ' ''.join(descripGrp.itertext()))
            #     definition_object, notes_extracted_from_sourcelink = xml_helpers.handle_multiple_sourcelinks_for_lang_definition(lang_grp, definition, name_to_id_map)
            # elif re.search(links_in_brackets, ''.join((descripGrp.itertext()))):
            #     print('test multi brack: ' ''.join(descripGrp.itertext()))
            #     definition_object, notes_extracted_from_sourcelink = xml_helpers.handle_multiple_sourcelinks_for_lang_definition(lang_grp, definition, name_to_id_map)
            # else:
            #     print('other: ' ''.join(descripGrp.itertext()))
            #     definition_object, notes_extracted_from_sourcelink = xml_helpers.create_definition_object(lang_grp, definition, name_to_id_map)
            #
            definition_objects, concept_notes_from_sources = xml_helpers.handle_definition(''.join(descripGrp.itertext()), name_to_id_map, lang_grp)

            for definition_object in definition_objects:
                definitions.append(definition_object)
                if definition_object.sourceLinks[0].sourceId == 'null':
                    print(definition_object)

            for con_note in concept_notes_from_sources:
                notes_for_concept.append(con_note)

            # if notes_extracted_from_sourcelink:
            #     for note in notes_extracted_from_sourcelink:
            #         notes_for_concept.append(note)

        termGrps = languageGrp.xpath('termGrp')

        for termGrp in termGrps:

            word = data_classes.Word(
                value='term',
                lang='est',
                lexemePublicity=is_public)

            # Get word (term) language and assign as attribute lang
            lang_term = languageGrp.xpath('language')[0].get('lang')
            word.lang = xml_helpers.match_language(lang_term)
            word.value = termGrp.xpath('term')[0].text

            # Parse descripGrp elements of languageGrp element
            for descripGrp in termGrp.xpath('descripGrp'):
                descrip_type = descripGrp.xpath('descrip/@type')[0]
                descrip_text = xml_helpers.get_description_value(descripGrp)
                valuestatecode_or_wordtype = descrip_text.split(">")[1].split("<")[0]

                # Parse word type as value state code or word type
                if descrip_type == 'Keelenditüüp':
                    if xml_helpers.is_type_word_type(valuestatecode_or_wordtype):
                        word.wordTypeCodes.append(xml_helpers.parse_word_types(valuestatecode_or_wordtype))
                        logger.debug('Added word type: %s', xml_helpers.parse_word_types(valuestatecode_or_wordtype))
                    else:
                        # Currently set the value state code in XML as value state code attribute value,
                        # it will be updated afterward
                        word.lexemeValueStateCode = valuestatecode_or_wordtype
                        logger.debug('Added word value state code: %s', word.lexemeValueStateCode)

                if descrip_type == 'Definitsioon':
                    definition_element_value = ''.join(descripGrp.itertext()).strip()

                    #print(definition_element_value)
                    #definition_object = None

                    # split_definitions = [definition for definition in re.split(r'\d+\.\s', definition_element_value) if definition]
                    #
                    # match_links_pattern = r'(?<!^)\[[^[]+\]'
                    # source_links_for_definition = []
                    #
                    # for split_definition in split_definitions:
                    #     split_definition = split_definition.strip().strip(';')
                    #     #print('see on siis see definitsioon, millega toimetan: ' + split_definition)
                    #     match_links = re.findall(match_links_pattern, split_definition)
                    #
                    #     if match_links:
                    #         for link in match_links:
                    #             split_definition = split_definition.replace(link, '')
                    #             link = link.strip('[]')
                    #             if ';' in link:
                    #                 separate_links = re.split('; ', link)
                    #                 #print('semikooloniga')
                    #                 #print(separate_links)
                    #                 for link in separate_links:
                    #                     value = link.strip()
                    #                     if '§' in link:
                    #                         value = re.split(r'§', link, 1)[0].strip()
                    #                         name = "§ " + re.split(r'§', link, 1)[1].strip()
                    #                     elif '1899' in link:
                    #                         value = '1899'
                    #                         name = link.replace('1899, ', '')
                    #                     elif '7149' in link:
                    #                         value = '7149'
                    #                         name = link.replace('7149, ', '')
                    #                     elif 'ConvRT' in link:
                    #                         value = 'ConvRT'
                    #                         name = link.replace('ConvRT ', '')
                    #                     else:
                    #                         value = link
                    #                         name = ''
                    #                     source_links_for_definition.append(data_classes.Sourcelink(
                    #                         sourceId=xml_helpers.find_source_by_name(name_to_id_map, value),
                    #                         value=value,
                    #                         name=name
                    #                     ))
                    #             else:
                    #                 if '§' in link:
                    #                     value = re.split(r'§', link, 1)[0].strip()
                    #                     name = "§ " + re.split(r'§', link, 1)[1].strip()
                    #                 elif '1899' in link:
                    #                     value = '1899'
                    #                     name = link.replace('1899, ', '')
                    #                 elif '7149' in link:
                    #                     value = '7149'
                    #                     name = link.replace('7149, ', '')
                    #                 elif 'ConvRT' in link:
                    #                     value = 'ConvRT'
                    #                     name = link.replace('ConvRT ', '')
                    #                 else:
                    #                     value = link
                    #                     name = ''
                    #                 source_links_for_definition.append(data_classes.Sourcelink(
                    #                     sourceId=xml_helpers.find_source_by_name(name_to_id_map, value),
                    #                     value=value,
                    #                     name=name
                    #                 ))
                    #     else:
                    #         continue
                    #
                    #
                    # definition_object = data_classes.Definition(
                    #     value=split_definition,
                    #     lang=word.lang,
                    #     definitionTypeCode='definitsioon',
                    #     sourceLinks=source_links_for_definition
                    # )

                    #print(definition_object)
                    definition_objects, con_notes = xml_helpers.handle_definition(definition_element_value, name_to_id_map, word.lang)

                    for defi_object in definition_objects:
                        definitions.append(defi_object)

                    for con_note in con_notes:
                        notes_for_concept.append(con_note)

                if descrip_type == 'Kontekst':

                    updated_value, source_links, concept_notes = xml_helpers.extract_usage_and_its_sourcelink(descripGrp, name_to_id_map)

                    if concept_notes:
                        for note in concept_notes:
                            #print('3: ' + updated_value)
                            notes_for_concept.append(note)
                    if source_links:
                        word.usages.append(
                            data_classes.Usage(
                                value=updated_value,
                                lang=xml_helpers.match_language(lang_term),
                                publicity=word.lexemePublicity,
                                sourceLinks=source_links)
                        )
                    else:
                        word.usages.append(
                            data_classes.Usage(
                                value=updated_value,
                                lang=xml_helpers.match_language(lang_term),
                                publicity=word.lexemePublicity)
                        )

                if descrip_type == 'Allikaviide':

                    descrip_element = descripGrp.xpath('./descrip[@type="Allikaviide"]')[0]

                    full_string = tostring(descrip_element, encoding="utf-8").decode('utf-8')

                    # Remove the outer tags to get only the inner XML
                    inner_xml = full_string.split('>', 1)[1].rsplit('<', 1)[0].strip()

                    sourcelinks, concept_notes_from_sourcelinks = xml_helpers.split_lexeme_sourcelinks_to_individual_sourcelinks(inner_xml, name_to_id_map)

                    if concept_notes_from_sourcelinks:
                        for note in concept_notes_from_sourcelinks:
                            notes_for_concept.append(note)

                    for link in sourcelinks:
                        word.lexemeSourceLinks.append(
                            data_classes.Sourcelink(
                                sourceId=link.sourceId,
                                value=link.value,
                                name=link.name
                            )
                        )

                if descrip_type == 'Märkus':
                    lexeme_notes = []

                    lexeme_note_raw = ''.join(descripGrp.itertext()).strip()
                    #print(lexeme_note_raw)
                    # [{MVS}09.06.2015] etc
                    pattern_for_initials_and_date = r'[\[|\{]\{*[^\[\]\{\}]*\}*\s*\d{2}\.\d{2}\.\d{4}[\]|\}]'
                    # [{KKA}4.06.2013]
                    # [{PSK}04/25/03]
                    pattern_for_initials_and_date_2 = r'\[\{\w*\}\d{1,2}[\.|\/]\d{1,2}[\.|\/]\d{2,4}\]'

                    # [SES 20.02.14]
                    # [SES 10/02/03]
                    pattern_for_initials_and_date_3 = r'\[\w*\s\d{1,2}[\/|\.]\d{1,2}[\/|\.]\d{1,2}\]'

                    pattern_for_sourcelink_in_the_end = r'\[.*\]$'

                    match_for_initials_and_date_3 = re.search(pattern_for_initials_and_date_3, lexeme_note_raw)
                    match_for_initials_and_date_2 = re.search(pattern_for_initials_and_date_2, lexeme_note_raw)
                    match_date_and_initials = re.search(pattern_for_initials_and_date, lexeme_note_raw)
                    match_sourcelink_in_the_end = re.search(pattern_for_sourcelink_in_the_end, lexeme_note_raw)

                    if match_for_initials_and_date_3:
                        #print('match_for_initials_and_date_3 + ' + lexeme_note_raw)
                        date = match_for_initials_and_date_3.group()
                        pattern = r'\d{1,2}[\/|\.]\d{1,2}[\/|\.]\d{1,2}\]'
                        match = re.search(pattern, date)
                        date_final = match.group().strip(']')
                        #print(date)

                        lexeme_note = data_classes.Lexemenote(
                            value=lexeme_note_raw.replace(date, ' [' + date_final + ']'),
                            lang=xml_helpers.detect_language(lexeme_note_raw),
                            publicity=True
                        )
                        #print(lexeme_note)
                        lexeme_notes.append(lexeme_note)

                    elif match_for_initials_and_date_2:
                        print('match_for_initials_and_date_2 + ' + lexeme_note_raw)
                        date_with_initials = match_for_initials_and_date_2.group()
                        parts = date_with_initials.split('}')
                        date_without_initials = parts[1]
                        print('date_without_initials: ' + '[' + date_without_initials)

                        note = lexeme_note_raw.replace(date_with_initials, '[' + date_without_initials)

                        lexeme_note = data_classes.Lexemenote(
                            value=note,
                            lang=xml_helpers.detect_language(note),
                            publicity=True
                        )
                        #print(lexeme_note)
                        lexeme_notes.append(lexeme_note)

                    elif match_date_and_initials:
                        print('match_date_and_initials: ' + lexeme_note_raw)
                        date = match_date_and_initials.group()

                        final_date = date[-11:]

                        if final_date[-1] == '}':
                            final_date = '{' + final_date
                            #print(final_date)
                        elif final_date[-1] == ']':
                            final_date = '[' + final_date
                            #print(final_date)
                        else:
                            print('midagi on valesti: ' + final_date)

                        lexeme_note_without_date = lexeme_note_raw.replace(date, '').strip()

                        pattern_for_sourcelink = r'\[.*\]'

                        link = re.search(pattern_for_sourcelink, lexeme_note_without_date)

                        if link:
                            #print(link.group())
                            sourcelink_value = link.group().strip('[]')
                            definition = lexeme_note_without_date.replace(link.group(), '').strip()
                            source_links = []
                            source_links.append(data_classes.Sourcelink(
                                sourceId=xml_helpers.find_source_by_name(name_to_id_map, sourcelink_value),
                                value=sourcelink_value
                            ))
                            lexeme_note = data_classes.Lexemenote(
                                value=definition + ' ' + final_date,
                                lang=xml_helpers.detect_language(definition),
                                publicity=True,
                                sourceLinks=source_links
                            )
                            lexeme_notes.append(lexeme_note)
                            #print(lexeme_note)
                        else:
                            definition = lexeme_note_without_date
                            lexeme_note = data_classes.Lexemenote(
                                value=definition + ' ' + final_date,
                                lang=xml_helpers.detect_language(definition),
                                publicity=True
                            )
                            lexeme_notes.append(lexeme_note)
                            #print(lexeme_note)
                            # print('definition: ' + definition + ' ' + final_date)
                            # print('sourcelink: ' + sourcelink_value)
                            # print('')

                    elif match_sourcelink_in_the_end:
                        sourcelink_value = match_sourcelink_in_the_end.group().strip('[]')
                        definition = lexeme_note_raw.replace(sourcelink_value, '')
                        #print('definition: ' + definition)
                        if 'EKSPERT' in sourcelink_value:
                            source_links = []
                            source_links.append(data_classes.Sourcelink(
                                sourceId=xml_helpers.find_source_by_name(name_to_id_map, 'EKSPERT'),
                                value=sourcelink_value
                            ))
                            notes_for_concept.append(data_classes.Note(
                                value=sourcelink_value,
                                lang='est',
                                publicity=False
                            ))
                            lexeme_note = data_classes.Lexemenote(
                                value=definition,
                                lang=xml_helpers.detect_language(definition),
                                publicity=True,
                                sourceLinks=source_links
                            )
                            lexeme_notes.append(lexeme_note)
                            #print(lexeme_note)
                        else:
                            source_links = []
                            source_links.append(data_classes.Sourcelink(
                                sourceId=xml_helpers.find_source_by_name(name_to_id_map, sourcelink_value),
                                value=sourcelink_value
                            ))
                            lexeme_note = data_classes.Lexemenote(
                                value=definition,
                                lang=xml_helpers.detect_language(definition),
                                publicity=True,
                                sourceLinks=source_links
                            )
                            lexeme_notes.append(lexeme_note)
                            #print(lexeme_note)
                    else:
                        lexeme_note = data_classes.Lexemenote(
                            value=lexeme_note_raw,
                            lang=xml_helpers.detect_language(lexeme_note_raw),
                            publicity=True,
                        )
                        lexeme_notes.append(lexeme_note)
                        #print(lexeme_note)
                        #print('mis siin toimub? ' + lexeme_note_raw)

                    for note in lexeme_notes:
                        word.lexemeNotes.append(note)

            words.append(word)

    # Remove and add notes if necessary
    words = xml_helpers.update_notes(words)

    for word in words:
        count = sum(1 for w in words if w.lang == word.lang)
        word.lexemeValueStateCode = xml_helpers.parse_value_state_codes(word.lexemeValueStateCode, count)

        logger.info('Added word - word value: %s, word language: %s, word is public: %s, word type: %s, '
                    'word value state code: %s',
                    word.value, word.lang, word.lexemePublicity, word.wordTypeCodes, word.lexemeValueStateCode)
        if word.usages:
            logger.info('Added word usage: %s', str(word.usages))
        if word.lexemeNotes:
            logger.info('Added word notes: %s', str(word.lexemeNotes))

    return words, definitions, notes_for_concept


# Write aviation concepts, all other concepts and domains to separate JSON files
def print_concepts_to_json(concepts, aviation_concepts):
    logger.debug('Number of concepts: %s', str(len(concepts)))
    logger.debug('Number of aviation concepts: %s', str(len(aviation_concepts)))

    output_folder = 'files/output'
    os.makedirs(output_folder, exist_ok=True)

    for concept_list, filename in [(concepts, 'concepts.json'),
                                   (aviation_concepts, 'aviation_concepts.json')]:

        concepts_json = json.dumps(
            [concept.__dict__ for concept in concept_list],
            default=lambda o: o.__dict__,
            indent=2,
            ensure_ascii=False
        )
        filepath = os.path.join(output_folder, filename)
        with open(filepath, 'w', encoding='utf8') as json_file:
            json_file.write(concepts_json)
            logger.info('Finished writing concepts: %s.', filename)


def transform_esterm_to_json(name_to_id_map):
# Opening the file, parsing, writing JSON files
    with open('files/input/esterm.xml', 'rb') as file:
        xml_content = file.read()

    parser = etree.XMLParser(encoding='UTF-16')
    root = etree.fromstring(xml_content, parser=parser)

    concepts, aviation_concepts = parse_mtf(root, name_to_id_map)

    print_concepts_to_json(concepts, aviation_concepts)

    logger.info('Finished transforming Esterm XML file to JSON files.')