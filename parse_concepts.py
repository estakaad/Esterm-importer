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
        # # For testing
        if counter % 10 == 0:
            logger.info(f'counter: {counter}')
            break

        counter += 1
        # End

        concept = data_classes.Concept(datasetCode='estermtest',
                                       manualEventOn=None,
                                       manualEventPerson=None,
                                       firstCreateEventOn=None,
                                       firstCreateEventPerson=None)
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
                    concept.firstCreateEventPerson = transac_element.text

        if modification_transac_grp_element is not None:
            modification_date_element = modification_transac_grp_element.find("date")
            if modification_date_element is not None:
                modification_date = modification_date_element.text
                modification_date_object = datetime.strptime(modification_date, "%Y-%m-%dT%H:%M:%S")
                concept.manualEventOn = modification_date_object.strftime('%d.%m.%Y')
                transac_element = modification_transac_grp_element.find("transac")
                if transac_element is not None:
                    concept.manualEventPerson = transac_element.text

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
                    note, source_search_value, source_display_value = xml_helpers.edit_note_without_multiple_languages(raw_note_value)

                if note_value:
                    concept.notes.append(data_classes.Note(
                        value=note_value,
                        lang='est',
                        publicity=True
                    ))
                else:
                    if source_search_value:
                        source_links = []

                        source_links.append(
                            data_classes.Sourcelink(
                                sourceId=xml_helpers.find_source_by_name(name_to_id_map, source_search_value),
                                searchValue=source_search_value,
                                value=source_display_value
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
                if ' ' not in worksheet:
                    worksheet = 'Tööleht: ' + worksheet

                concept.forums.append(data_classes.Forum(
                    value=worksheet)
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
        words, definitions = parse_words(conceptGrp, name_to_id_map)

        for word in words:
            concept.words.append(word)

        for definition in definitions:
            #concept.definitions.append(xml_helpers.extract_definition_source_links(definition, updated_sources))
            concept.definitions.append(definition)

        list_to_append.append(concept)
        logger.info('Finished parsing concept.')

    return concepts, aviation_concepts


# Parse word elements in one concept in XML
def parse_words(conceptGrp, name_to_id_map):

    words = []
    definitions = []
    is_public = xml_helpers.are_terms_public(conceptGrp)
    logger.debug('Is concept public? %s', is_public)

    for languageGrp in conceptGrp.xpath('languageGrp'):

        # Handle definitions which are on the languageGrp level, not on the termGrp level
        for descripGrp in languageGrp.xpath('descripGrp[descrip/@type="Definitsioon"]'):

            lang_grp = languageGrp.xpath('language')[0].get('lang')
            logger.debug('def language: %s', lang_grp)
            lang_grp = xml_helpers.match_language(lang_grp)
            logger.debug(('def language after matching: %s', lang_grp))

            definition = descripGrp.find('./descrip')

            semicolon_in_brackets = r'\s\[.*;.*\]'

            if re.search(semicolon_in_brackets, ''.join(descripGrp.itertext())):
                definition_object = xml_helpers.handle_multiple_sourcelinks_for_lang_definition(lang_grp, definition, name_to_id_map)
                #print(definition_object)
            else:
                definition_object = xml_helpers.create_definition_object(lang_grp, definition, name_to_id_map)

            definitions.append(definition_object)

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
                    individual_definitions = xml_helpers.split_and_preserve_xml(descripGrp)
                    individual_definitions = xml_helpers.fix_xml_fragments(individual_definitions, 'descrip')

                    for definition in individual_definitions:

                        definition_element = etree.fromstring(definition)

                        definition_object = xml_helpers.create_definition_object(word.lang, definition_element, name_to_id_map)

                        definitions.append(definition_object)

                if descrip_type == 'Kontekst':

                    updated_value, source_links = xml_helpers.extract_usage_and_its_sourcelink(descripGrp, name_to_id_map)

                    word.usages.append(
                        data_classes.Usage(
                            value=updated_value,
                            lang=xml_helpers.match_language(lang_term),
                            publicity=word.lexemePublicity,
                            sourceLinks=source_links)
                    )

                if descrip_type == 'Allikaviide':

                    descrip_element = descripGrp.xpath('./descrip[@type="Allikaviide"]')[0]

                    full_string = tostring(descrip_element, encoding="utf-8").decode('utf-8')

                    # Remove the outer tags to get only the inner XML
                    inner_xml = full_string.split('>', 1)[1].rsplit('<', 1)[0].strip()

                    sourcelinks = xml_helpers.split_lexeme_sourcelinks_to_individual_sourcelinks(inner_xml, name_to_id_map)

                    for link in sourcelinks:
                        if link.value.startswith('EKSPERT'):
                            word.lexemeSourceLinks.append(
                                data_classes.Sourcelink(
                                    sourceId=link.sourceId,
                                    searchValue=link.searchValue,
                                    value=link.value
                                )
                            )
                        else:
                            word.lexemeSourceLinks.append(
                                data_classes.Sourcelink(
                                    sourceId=link.sourceId,
                                    searchValue=link.searchValue,
                                    value=link.value
                                )
                            )


                if descrip_type == 'Märkus':
                    note_value = ''.join(descripGrp.itertext()).strip().replace('\u200b', '')

                    text_before_bracket, date_string, source, tail = \
                        xml_helpers.extract_lexeme_note_and_its_sourcelinks(note_value)

                    source_links = []

                    if source.startswith('EKSPERT '):
                        source = source.replace('EKSPERT ', '').strip()
                        display_value = 'EKSPERT ' + source

                        source_links.append(
                            data_classes.Sourcelink(
                                sourceId=xml_helpers.find_source_by_name(name_to_id_map, source),
                                searchValue=source,
                                value=display_value
                            )
                        )
                    else:
                        if source:
                            if tail:
                                display_value = source + ' ' + tail
                            else:
                                display_value = source

                            source_links.append(
                                data_classes.Sourcelink(
                                    sourceId=xml_helpers.find_source_by_name(name_to_id_map, source),
                                    searchValue=source,
                                    value=display_value
                                )
                            )

                    if word.lang == 'est':
                        note_lang = 'est'
                    else:
                        note_lang = xml_helpers.detect_language(text_before_bracket)

                    if source_links:
                        word.lexemeNotes.append(
                            data_classes.Lexemenote(
                                value=text_before_bracket,
                                lang=note_lang,
                                publicity=word.lexemePublicity,
                                sourceLinks=source_links
                            )
                        )
                    else:
                        word.lexemeNotes.append(
                            data_classes.Lexemenote(
                                value=text_before_bracket,
                                lang=note_lang,
                                publicity=word.lexemePublicity
                            )
                        )

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

    return words, definitions


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