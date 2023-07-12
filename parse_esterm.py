from lxml import etree
import json
import xml_helpers
import os
import data_classes
import log_config


logger = log_config.get_logger()


# Parse the whole Esterm XML and return aviation concepts, all other concepts and the sources of the concepts
def parse_mtf(root):
    concepts = []
    sources = []
    aviation_concepts = []
    domain_entries = []

    for conceptGrp in root.xpath('/mtf/conceptGrp'):
        concept = data_classes.Concept(datasetCode='termapi')
        logger.info("Started parsing concept.")

        type_of_concept = xml_helpers.type_of_concept(conceptGrp)

        if type_of_concept == 'source':
            list_to_append = sources
            logger.debug('Concept will be added to the list of sources.')
        elif type_of_concept == 'domain':
            list_to_append = domain_entries
            logger.debug('Concept will be added to the list of domains.')
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
                concept.notes.append(data_classes.Note(
                    value=xml_helpers.get_description_value(descrip_element),
                    lang='est',
                    publicity=True
                ))
                if descrip_element_value:
                    logger.debug('Added note: %s', descrip_element_value)
            # Get concept tööleht and add its value to concept forum list.
            elif descrip_element.get('type') == 'Tööleht':
                concept.forums.append(data_classes.Forum(
                    value=descrip_element_value
                ))
                if descrip_element_value:
                    logger.debug('Added tööleht to forums: %s', descrip_element_value)
            elif descrip_element.get('type') == 'Sisemärkus':
                concept.forums.append(data_classes.Forum(
                    value=descrip_element_value
                ))
                if descrip_element_value:
                    logger.debug('Added sisemärkus to forums: %s', descrip_element_value)
            # Get concept context and add its value to the concept usage list NB - or notes !?!? MIS KEELES?
            elif descrip_element.get('type') == 'Kontekst':
                concept.notes.append(data_classes.Note(
                    value=descrip_element_value,
                    lang='est',
                    publicity=True
                ))
                if descrip_element_value:
                    logger.debug('Added kontekst to notes: %s', descrip_element_value)

        logger.info('Added concept domains: %s', str(concept.domains))
        if concept.notes:
            logger.info('Added concept notes: %s', str(concept.notes))
        if concept.forums:
            logger.info('Added concept forum: %s', str(concept.forums))
        # Concept level data is parsed, now to parsing word (term) level data
        words, definitions = parse_words(conceptGrp, concept)

        for word in words:
            concept.words.append(word)

        for definition in definitions:
            concept.definitions.append(definition)

        list_to_append.append(concept)
        logger.info('Finished parsing concept.')

    return concepts, sources, aviation_concepts, domain_entries


# Parse word elements in one concept in XML
def parse_words(conceptGrp, concept):

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

            descrip_text = ''.join(descripGrp.xpath('descrip')[0].itertext())
            definitions.append(xml_helpers.parse_definition(descrip_text, descripGrp, lang_grp))

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

                # Parse word type as value state code or word type
                if descrip_type == 'Keelenditüüp':

                    if xml_helpers.is_type_word_type(descrip_text):
                        word.word_type = xml_helpers.parse_word_types(descrip_text)
                        logger.debug('Added word type: %s', word.word_type)
                    else:
                        # Currently set the value state code in XML as value state code attribute value,
                        # it will be updated afterwards
                        word.lexemeValueStateCode = descrip_text.split(">")[1].split("<")[0]
                        logger.debug('Added word value state code: %s', word.lexemeValueStateCode)

                if descrip_type == 'Definitsioon':
                    #definitions.append(xml_helpers.parse_definition(descrip_text, descripGrp, xml_helpers.match_language(lang_term)))
                    definitions.append(''.join(descripGrp.itertext()))

                if descrip_type == 'Kontekst':
                    word.usages.append(
                        data_classes.Usage(
                            value=''.join(descripGrp.itertext()),
                            lang=xml_helpers.match_language(lang_term),
                            publicity=word.lexemePublicity)
                    )

                if descrip_type == 'Allikas':
                    print('Allikas')

                if descrip_type == 'Märkus':
                    word.lexemeNotes.append(
                        data_classes.lexemeNote(value=descrip_text, lang=word.lang, publicity=word.lexemePublicity))

            words.append(word)

    # Remove and add notes if necessary
    words = xml_helpers.update_notes(words)

    for word in words:
        count = sum(1 for w in words if w.lang == word.lang)
        #print(count, ' - ', word)
        word.lexemeValueStateCode = xml_helpers.parse_value_state_codes(word.lexemeValueStateCode, count)

        logger.info('Added word - word value: %s, word language: %s, word is public: %s, word type: %s, '
                    'word value state code: %s',
                    word.value, word.lang, word.lexemePublicity, word.wordTypeCodes, word.lexemeValueStateCode)
        if word.usages:
            logger.info('Added word usage: %s', str(word.usages))
        if word.lexemeNotes:
            logger.info('Added word notes: %s', str(word.lexemeNotes))

    return words, definitions


# Write aviation concepts, all other concepts and sources of the concepts to three separate JSON files
def print_concepts_to_json(concepts, sources, aviation_concepts, domain_entries):

    logger.debug('Number of concepts: %s', str(len(concepts)))
    logger.debug('Number of aviation concepts: %s', str(len(aviation_concepts)))
    logger.debug('Number of sources: %s', str(len(sources)))
    logger.debug('Number of domain entries: %s', str(len(domain_entries)))

    output_folder = 'output'
    os.makedirs(output_folder, exist_ok=True)

    for concept_list, filename in [(concepts, 'concepts.json'),
                                   (sources, 'sources.json'),
                                   (aviation_concepts, 'aviation_concepts.json'),
                                   (domain_entries, 'domains.json')]:
        concepts_json = json.dumps(
            [concept.__dict__ for concept in concept_list],
            default=lambda o: o.__dict__,
            indent=4,
            ensure_ascii=False
        )
        with open(os.path.join(output_folder, filename), 'w', encoding='utf8') as json_file:
            json_file.write(concepts_json)
            logger.info('Finished writing concepts: %s.', filename)


def transform_esterm_to_json():
# Opening the file, parsing, writing JSON files
    with open('input/esterm.xml', 'rb') as file:
        xml_content = file.read()

    parser = etree.XMLParser(encoding='UTF-16')
    root = etree.fromstring(xml_content, parser=parser)

    concepts, sources, aviation_concepts, domain_entries = parse_mtf(root)
    print_concepts_to_json(concepts, sources, aviation_concepts, domain_entries)

    logger.info('Finished transforming Esterm XML file to JSON files.')