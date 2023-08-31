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
def parse_mtf(root, updated_sources):
    concepts = []
    aviation_concepts = []

    # For testing #
    #counter = 1

    for conceptGrp in root.xpath('/mtf/conceptGrp'):
        # For testing
        # if counter % 300 == 0:
        #     logger.info(f'counter: {counter}')
        #     break
        #
        # counter += 1
        # End

        concept = data_classes.Concept(datasetCode='et1608')
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

        # Parse concept level descrip elements and add their values as attributes to Concept
        for descrip_element in conceptGrp.xpath('descripGrp/descrip'):

            descrip_element_value = etree.tostring(descrip_element, encoding='unicode', method='text')

            # Get concept domain and add to the list of concept domains
            if descrip_element.get('type') == 'Valdkonnaviide':
                for domain in descrip_element_value.split(';'):
                    domain = domain.strip()
                    if domain:
                        concept.domains.append(data_classes.Domain(code=domain, origin='lenoch'))

            # Get concept notes and add to the list of concept notes. !?!?! MIS KEELES?
            elif descrip_element.get('type') == 'Märkus':
                raw_note_value = xml_helpers.get_description_value(descrip_element)

                # TODO: check this out.
                # What if source is EKSPERT? Do expert names have to be removed? Currently they are.

                if xml_helpers.does_note_contain_multiple_languages(raw_note_value):
                    note_value = xml_helpers.edit_note_with_multiple_languages(raw_note_value)
                else:
                    note_value = xml_helpers.edit_note_without_multiple_languages(raw_note_value)

                concept.notes.append(data_classes.Note(
                    value=note_value,
                    lang='est',
                    publicity=True
                ))

                if descrip_element_value:
                    logger.debug('Added note: %s', descrip_element_value)

            # Get concept tööleht and add its value to concept forum list.
            elif descrip_element.get('type') == 'Tööleht':
                concept.forums.append(data_classes.Forum(
                    value=descrip_element_value.replace("\n", "").replace("\t", "")
                ))
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

            # Currently add "Kontekst" as concept notes and
            # its language is always Estonian because we don't know any better
            elif descrip_element.get('type') == 'Kontekst':
                concept.notes.append(data_classes.Note(
                    value=descrip_element_value,
                    lang='est',
                    publicity=xml_helpers.are_terms_public(conceptGrp)
                ))
                if descrip_element_value:
                    logger.debug('Added kontekst to notes: %s', descrip_element_value)

        logger.info('Added concept domains: %s', str(concept.domains))
        if concept.notes:
            logger.info('Added concept notes: %s', str(concept.notes))
        if concept.forums:
            logger.info('Added concept forum: %s', str(concept.forums))

        # Concept level data is parsed, now to parsing word (term) level data
        words, definitions = parse_words(conceptGrp, concept, updated_sources)

        for word in words:
            concept.words.append(word)

        for definition in definitions:
            #concept.definitions.append(xml_helpers.extract_definition_source_links(definition, updated_sources))
            concept.definitions.append(definition)

        list_to_append.append(concept)
        logger.info('Finished parsing concept.')

    return concepts, aviation_concepts


# Parse word elements in one concept in XML
def parse_words(conceptGrp, concept, updated_sources):

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

            definition_object = xml_helpers.create_definition_object(lang_grp, definition, updated_sources)

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

                        definition_object = xml_helpers.create_definition_object(word.lang, definition_element, updated_sources)

                        definitions.append(definition_object)

                if descrip_type == 'Kontekst':

                    updated_value, source_links = xml_helpers.extract_usage_and_its_sourcelink(descripGrp, updated_sources)

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

                    sourcelinks = xml_helpers.split_lexeme_sourcelinks_to_individual_sourcelinks(inner_xml, updated_sources)

                    for link in sourcelinks:
                        if link.value.startswith('EKSPERT'):
                            word.lexemeSourceLinks.append(
                                data_classes.sourceLink(
                                    sourceId=link.sourceId,
                                    searchValue=link.searchValue,
                                    value=link.value
                                )
                            )
                        else:
                            word.lexemeSourceLinks.append(
                                data_classes.sourceLink(
                                    sourceId=link.sourceId,
                                    searchValue=link.searchValue,
                                    value=link.searchValue + ((' ' + link.value) if link.value else '')
                                )
                            )

                if descrip_type == 'Märkus':
                    note_value = ''.join(descripGrp.itertext()).strip().replace('\u200b', '')

                    text_before_bracket, date_string, source, tail = \
                        xml_helpers.extract_lexeme_note_and_its_sourcelinks(note_value)

                    source_links = []

                    if source:
                        if tail:
                            display_value = source + ' ' + tail
                        else:
                            display_value = source

                        source_links.append(
                            data_classes.sourceLink(
                                sourceId=xml_helpers.find_source_by_name(updated_sources, source),
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
                            data_classes.lexemeNote(
                                value=text_before_bracket,
                                lang=note_lang,
                                publicity=word.lexemePublicity,
                                sourceLinks=source_links
                            )
                        )
                    else:
                        word.lexemeNotes.append(
                            data_classes.lexemeNote(
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
        with open(os.path.join(output_folder, filename), 'w', encoding='utf8') as json_file:
            json_file.write(concepts_json)
            logger.info('Finished writing concepts: %s.', filename)


def transform_esterm_to_json(updated_sources):
# Opening the file, parsing, writing JSON files
    with open('files/input/esterm.xml', 'rb') as file:
        xml_content = file.read()

    parser = etree.XMLParser(encoding='UTF-16')
    root = etree.fromstring(xml_content, parser=parser)

    concepts, aviation_concepts = parse_mtf(root, updated_sources)
    print_concepts_to_json(concepts, aviation_concepts)

    logger.info('Finished transforming Esterm XML file to JSON files.')