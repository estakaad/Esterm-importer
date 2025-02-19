from datetime import datetime
from lxml import etree
import json
import expert_sources_helpers
import xml_helpers
import os
import data_classes
import log_config
import re
from lxml.etree import tostring

logger = log_config.get_logger()


# Parse the whole Esterm XML and return aviation concepts, all other concepts and the sources of the concepts
def parse_mtf(root, name_to_id_map, expert_names_to_ids_map, term_sources_to_ids_map):
    concepts = []
    # For testing #
    counter = 1
    for conceptGrp in root.xpath('/mtf/conceptGrp'):

        # # # # # For testing
        # if counter % 10000 == 0:
        #    logger.info(f'counter: {counter}')
        #    break
        #
        # counter += 1
        # End

        concept = data_classes.Concept(datasetCode='est0503',
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
            logger.debug('Concept is actually a domain. Skipping it.')
            continue

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

        if modification_transac_grp_element is not None:
            modification_date_element = modification_transac_grp_element.find("date")
            if modification_date_element is not None:
                modification_date = modification_date_element.text
                modification_date_object = datetime.strptime(modification_date, "%Y-%m-%dT%H:%M:%S")
                concept.manualEventOn = modification_date_object.strftime('%d.%m.%Y')
                transac_element = modification_transac_grp_element.find("transac")
                if transac_element is not None:
                    concept.manualEventBy = xml_helpers.map_initials_to_names(transac_element.text)

        # Parse concept level descrip elements and add their values as attributes to Concept
        for descrip_element in conceptGrp.xpath('descripGrp/descrip'):

            descrip_element_value = etree.tostring(descrip_element, encoding='unicode', method='text')

            # Get concept domain and add to the list of concept domains
            if descrip_element.get('type') == 'Valdkonnaviide':
                for domain in descrip_element_value.split(';'):
                    domain = domain.strip()
                    if domain:
                        concept.domains.append(data_classes.Domain(code=domain, origin='lenoch'))

            if descrip_element.get('type') == 'Mõistetüüp':
                tag_name = xml_helpers.map_concept_type_to_tag_name(''.join(descrip_element.itertext()).strip())
                concept.tags.append(tag_name)

            if descrip_element.get('type') == 'Päritolu':
                origin = ''.join(descrip_element.itertext()).strip()
                concept.notes.append(
                    data_classes.Note(
                        value='Päritolu: ' + origin,
                        lang='est',
                        publicity=False
                    )
                )

            if descrip_element.get('type') == 'Tunnus':
                tunnus = ''.join(descrip_element.itertext()).strip(';')
                concept.notes.append(
                    data_classes.Note(
                        value='Tunnus: ' + tunnus,
                        lang='est',
                        publicity=False
                    )
                )

            if descrip_element.get('type') == 'Alamvaldkond_':
                subdomain = ''.join(descrip_element.itertext()).strip()
                subdomain = subdomain.replace('|', '; ')
                concept.notes.append(
                    data_classes.Note(
                        value='Valdkond ICAO lisade põhjal loodud klassifikaatori järgi: ' + subdomain,
                        lang='est',
                        publicity=True
                    )
                )
            if descrip_element.get('type') == 'Staatus':
                concept_status = ''.join(descrip_element.itertext()).strip()
                if concept_status == 'KTTG kinnitatud':
                    concept.notes.append(
                        data_classes.Note(
                            value='Staatus: kinnitatud',
                            lang='est',
                            publicity=True,
                            sourceLinks=[data_classes.Sourcelink(
                                sourceId=xml_helpers.find_source_by_name(name_to_id_map, 'KTTG'),
                                value='KTTG',
                                sourceLinkName=''
                            )]
                        )
                    )
                elif concept_status == 'KTTGs arutlusel':
                    concept.notes.append(
                        data_classes.Note(
                            value='Staatus: arutlusel',
                            lang='est',
                            publicity=True,
                            sourceLinks=[data_classes.Sourcelink(
                                sourceId=xml_helpers.find_source_by_name(name_to_id_map, 'KTTG'),
                                value='KTTG',
                                sourceLinkName=''
                            )]
                        )
                    )
                elif concept_status == 'komisjonis arutlusel':
                    concept.notes.append(
                        data_classes.Note(
                            value='Staatus: arutlusel',
                            lang='est',
                            publicity=True,
                            sourceLinks=[data_classes.Sourcelink(
                                sourceId=xml_helpers.find_source_by_name(name_to_id_map, 'LTK'),
                                value='LTK',
                                sourceLinkName=''
                            )]
                        )
                    )
                elif concept_status == 'komisjoni kinnitatud':
                    concept.notes.append(
                        data_classes.Note(
                            value='Staatus: kinnitatud',
                            lang='est',
                            publicity=True,
                            sourceLinks=[data_classes.Sourcelink(
                                sourceId=xml_helpers.find_source_by_name(name_to_id_map, 'LTK'),
                                value='LTK',
                                sourceLinkName=''
                            )]
                        )
                    )
                elif concept_status == 'terminiprobleem':
                    concept.notes.append(
                        data_classes.Note(
                            value='Staatus: terminiprobleem',
                            lang='est',
                            publicity=False,
                            sourceLinks=[]
                        )
                    )
                else:
                    concept.notes.append(
                        data_classes.Note(
                            value='Staatus: ' + concept_status,
                            lang='est',
                            publicity=True
                        )
                    )

            # Get concept notes and add to the list of concept notes.
            elif descrip_element.get('type') == 'Märkus':
                raw_note_value = xml_helpers.get_description_value(descrip_element)
                note_value = ''.join(descrip_element.itertext()).strip()

                if xml_helpers.does_note_contain_ampersand_in_sourcelink(note_value):
                    lexeme_notes, concept_notes = xml_helpers.handle_ampersand_notes('concept', note_value,
                                                                                     term_sources_to_ids_map)
                    for note in concept_notes:
                        if note.value.startswith('KONTROLLIDA: '):
                            concept.tags.append('term kontrolli mõistet')
                        concept.notes.append(note)

                # Does note contain multiple languages?
                elif xml_helpers.does_note_contain_multiple_languages(raw_note_value):
                    if note_value.startswith('{') and note_value.endswith('}'):
                        concept.notes.append(data_classes.Note(
                            value=note_value.strip('{}'),
                            lang='est',
                            publicity=False,
                            sourceLinks=None
                        ))
                    #note_value = xml_helpers.edit_note_with_multiple_languages(raw_note_value)
                    # Does note end with terminologist initials and date in curly braces?
                    elif note_value.endswith('}'):
                        # Multiple initials
                        if '&' in note_value:

                            sourcelinks = []


                            parts = note_value.split('{')

                            initials_and_date = parts[1].split('&')

                            for p in initials_and_date:
                                p = p.strip().rstrip('}')
                                p = p.split()[0]
                                note_value = note_value.replace(p, '')
                                name, source_id = term_sources_to_ids_map.get(p, ("", None))

                                sourcelinks.append(data_classes.Sourcelink(
                                    sourceId=source_id,
                                    value=name,
                                    sourceLinkName=''
                                ))

                            note_value = note_value.replace(' &  ', '')
                            note_value = note_value.replace(' { & }', '')
                            note_value = note_value.replace('{&  ', '')
                            concept.notes.append(
                                data_classes.Note(
                                    value=note_value,
                                    lang='est',
                                    publicity=True,
                                    sourceLinks=[sourcelinks]
                                )
                            )

                        # One set of initials
                        else:
                            if 'EKSPERT' in note_value:
                                concept.tags.append('term kontrolli mõistet')
                                concept.notes.append(
                                    data_classes.Note(
                                        value='KONTROLLIDA: ' + note_value,
                                        lang='est',
                                        publicity=False,
                                        sourceLinks=[]
                                    )
                                )
                            else:
                                last_opening_brace = note_value.rfind('{')
                                if last_opening_brace != -1:
                                    end_brace_pos = note_value.find('}', last_opening_brace)
                                    if end_brace_pos != -1:
                                        # Extract the string between the braces
                                        inside_braces = note_value[last_opening_brace + 1:end_brace_pos]
                                        # Split the string by space and take the first part
                                        # This works for both single and multiple initials
                                        initials = inside_braces.split()[0]

                                key = initials
                                name, source_id = term_sources_to_ids_map.get(key, ("", None))

                                source = data_classes.Sourcelink(
                                    sourceId=source_id,
                                    value=name,
                                    sourceLinkName=''
                                )
                                concept.notes.append(
                                    data_classes.Note(
                                        value=note_value.replace('{' + initials + ' ', '{'),
                                        lang='est',
                                        publicity=True,
                                        sourceLinks=[source]
                                    )
                                )
                    elif 'ekspert' in note_value.lower():
                        concept.tags.append('term kontrolli mõistet')
                        concept.notes.append(
                            data_classes.Note(
                                value='KONTROLLIDA: ' + note_value,
                                lang='est',
                                publicity=True,
                                sourceLinks=None
                            )
                        )
                    else:
                        concept.notes.append(
                            data_classes.Note(
                                value=note_value,
                                lang='est',
                                publicity=True,
                                sourceLinks=None
                            )
                        )
                # In case note does not contain multiple languages...
                else:
                    # Look for notes which are difficult to parse. They have [] and/or {} in other places
                    # than in the end of the string
                    # Unless they begin and end with {}. Then Make the whole note not public.
                    if note_value.startswith('{') and note_value.endswith('}'):
                        concept.notes.append(data_classes.Note(
                            value=note_value.strip('{}'),
                            lang='est',
                            publicity=False,
                            sourceLinks=None
                        ))

                    else:
                        term_pairs = ['ÜMT/ÜAU', 'AKE/ALK', 'ELS/ETM', 'MRS/MST', 'PTE/PTH', 'IKS/IFH']

                        # Perform the check for brackets/braces in the middle of the string
                        if any(char in note_value[:-50] for char in '[]{}'):
                            concept.tags.append('term kontrolli mõistet')
                            concept.notes.append(data_classes.Note(
                                value='KONTROLLIDA: ' + note_value,
                                lang='est',
                                publicity=False,
                                sourceLinks=None
                            ))
                        else:
                            pair_found = False
                            for pair in term_pairs:
                                if pair in note_value:
                                    conceptnotes = xml_helpers.handle_note_with_double_initials_in_concept_level(note_value,
                                                   term_sources_to_ids_map,
                                                   expert_names_to_ids_map,
                                                   name_to_id_map)
                                    for cn in conceptnotes:
                                        concept.notes.append(cn)
                                    pair_found = True
                                    break

                            if not pair_found:

                                # Now we've got to the proper notes which we should be able to parse
                                lexeme_notes_with_sourcelinks, concept_notes_with_sourcelinks = \
                                    xml_helpers.handle_notes_with_brackets('concept', name_to_id_map,
                                                                           expert_names_to_ids_map, term_sources_to_ids_map, note_value)

                                for note in concept_notes_with_sourcelinks:
                                    concept.notes.append(note)
                                    if note.value.startswith('KONTROLLIDA'):
                                        concept.tags.append('term kontrolli mõistet')

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
        words, definitions, concept_notes_from_lang = parse_words(conceptGrp, name_to_id_map, expert_names_to_ids_map, term_sources_to_ids_map)

        for word in words:
            concept.words.append(word)

        for definition in definitions:
            concept.definitions.append(definition)

        for concept_note_from_lang in concept_notes_from_lang:
            concept.notes.append(concept_note_from_lang)

        concept.notes = [note for note in concept.notes if isinstance(note, data_classes.Note) and note.value.strip()]

        if concept.manualEventOn == '30.12.2004':
            xml_helpers.make_old_comments_not_public(concept)

        # Make defence concepts not public
        for d in concept.domains:
            if d.code.startswith('DE'):
                print(concept.conceptIds)
                xml_helpers.make_defence_concepts_not_public(concept)

        # Concept should be ready by now!

        for definition in concept.definitions:
            if definition.value.startswith('{'):
                definition.value = re.sub(r'^{[^}]*}', '', definition.value)

        concept.notes.sort(key=lambda x: x.publicity, reverse=True)

        concepts.append(concept)

        logger.debug('Concept will be added to the general list of concepts.')

        logger.info('Finished parsing concept.')

    return concepts


# Parse word elements in one concept in XML
def parse_words(conceptGrp, name_to_id_map, expert_names_to_ids_map, term_sources_to_ids_map):

    words = []
    definitions = []
    notes = []
    is_public = xml_helpers.are_terms_public(conceptGrp)
    logger.debug('Is concept public? %s', is_public)

    for languageGrp in conceptGrp.xpath('languageGrp'):

        # Handle definitions which are on the languageGrp level, not on the termGrp level
        for descripGrp in languageGrp.xpath('descripGrp[descrip/@type="Definitsioon"]'):

            lang_grp = languageGrp.xpath('language')[0].get('lang')
            logger.debug('Definition language: %s', lang_grp)
            lang_grp = xml_helpers.match_language(lang_grp)
            logger.debug(('Definition language after matching: %s', lang_grp))

            definition_objects = xml_helpers.handle_definition(''.join(descripGrp.itertext()), name_to_id_map, lang_grp, expert_names_to_ids_map)

            for definition_object in definition_objects:
                if definition_object.sourceLinks and definition_object.sourceLinks[0].value.startswith('http'):
                    definition_object.value += ' [' + definition_object.sourceLinks[0].value + ']'
                    del definition_object.sourceLinks[0]
                definitions.append(definition_object)
                if definition_object.sourceLinks and definition_object.sourceLinks[0].sourceId == 'null':
                    print(definition_object)

        for descripGrp in languageGrp.xpath('descripGrp[descrip/@type="Märkus"]'):

            note_raw = ''.join(descripGrp.itertext()).strip()

            if note_raw == 'An aircraft system which provides head-up guidance to the pilot during flight. ' \
                           'It includes the display elements, sensors, computers and power supplies, ' \
                           'indications and controls. It may receive inputs from an airborne navigation ' \
                           'system or flight guidance system. [A&GM-4]':
                notes.append(data_classes.Note(
                    value='An aircraft system which provides head-up guidance to the pilot during flight. '
                          'It includes the display elements, sensors, computers and power supplies, '
                          'indications and controls. It may receive inputs from an airborne navigation '
                          'system or flight guidance system.',
                    lang='est',
                    publicity=True,
                    sourceLinks=[data_classes.Sourcelink(
                        sourceId=xml_helpers.find_source_by_name(name_to_id_map,'A&GM-4'),
                        value='A&GM-4',
                        sourceLinkName=''
                    )]
                ))

            elif xml_helpers.does_note_contain_ampersand_in_sourcelink(note_raw):

                lexeme_notes, concept_notes = xml_helpers.handle_ampersand_notes('concept', note_raw,
                                                                                 term_sources_to_ids_map)
                for note in concept_notes:
                    notes.append(note)
            else:
                note = xml_helpers.parse_lang_level_note(note_raw, name_to_id_map, expert_names_to_ids_map, term_sources_to_ids_map)

                notes.append(note)

        termGrps = languageGrp.xpath('termGrp')

        for termGrp in termGrps:

            word = data_classes.Word(
                valuePrese='term',
                lang='est',
                lexemePublicity=is_public)

            # Get word (term) language and assign as attribute lang
            lang_term = languageGrp.xpath('language')[0].get('lang')
            word.lang = xml_helpers.match_language(lang_term)
            word.valuePrese = termGrp.xpath('term')[0].text

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

                    definition_objects = xml_helpers.handle_definition(definition_element_value, name_to_id_map, word.lang, expert_names_to_ids_map)

                    for defi_object in definition_objects:
                        definitions.append(defi_object)

                if descrip_type == 'Kontekst':
                    kontekst_element_value = ''.join(descripGrp.itertext()).strip()

                    usages = xml_helpers.split_context_to_parts(kontekst_element_value)

                    for usage in usages:

                        usage_object = xml_helpers.parse_context_like_note(usage, name_to_id_map, expert_names_to_ids_map, term_sources_to_ids_map)

                        if usage_object.value.startswith('KONTROLLIDA:'):
                            word.lexemeTags.append('term kontrolli ilmikut')

                        if usage_object:
                            print(usage_object.lang)
                            if usage_object.sourceLinks:
                                if usage_object.sourceLinks[0].value.startswith('http'):
                                    value = usage_object.value + ' [' + usage_object.sourceLinks[0].value + ']'
                                    word.usages.append(
                                        data_classes.Usage(
                                            value=value,
                                            lang=xml_helpers.match_language(lang_term),
                                            publicity=word.lexemePublicity)
                                    )
                                    del usage_object.sourceLinks[0]
                                else:
                                    word.usages.append(usage_object)
                            else:
                                word.usages.append(usage_object)
                            print(usage_object)

                if descrip_type == 'Allikaviide':

                    descrip_element = descripGrp.xpath('./descrip[@type="Allikaviide"]')[0]

                    lexeme_sources = ''.join(descrip_element.itertext()).strip().strip('[]')

                    if ';' in lexeme_sources:
                        links = lexeme_sources.split(';')
                    elif '][' in lexeme_sources:
                        links = lexeme_sources.split('][')
                    elif '] [' in lexeme_sources:
                        links = lexeme_sources.split('] [')
                    else:
                        links = [lexeme_sources]


                    for link in links:
                        link = link.strip().strip('[]')
                        value, name, expert_name, expert_type = xml_helpers.separate_sourcelink_value_from_name(link)

                        value = value.strip('[]')

                        if value == '{TMA}':
                            key = 'TMA'
                            name, source_id = term_sources_to_ids_map.get(key, ("", None))
                            word.lexemeSourceLinks.append(
                                data_classes.Sourcelink(
                                    sourceId=source_id,
                                    value=name,
                                    sourceLinkName=''
                                )
                            )
                        elif expert_type:
                            sourceid = expert_sources_helpers.get_expert_source_id_by_name_and_type(expert_name, expert_type, expert_names_to_ids_map)
                            word.lexemeSourceLinks.append(
                                data_classes.Sourcelink(
                                    sourceId=sourceid,
                                    value=expert_type,
                                    sourceLinkName=''
                                )
                            )
                        else:
                            sourceid = xml_helpers.find_source_by_name(name_to_id_map, value)

                            word.lexemeSourceLinks.append(
                                data_classes.Sourcelink(
                                    sourceId=sourceid,
                                    value=value,
                                    sourceLinkName=name
                                )
                            )

                if descrip_type == 'Märkus':
                    lexeme_note_raw = ''.join(descripGrp.itertext()).strip()

                    if lexeme_note_raw.startswith('{') and lexeme_note_raw.endswith('}'):
                        lexeme_notes_with_sourcelinks, concept_notes_with_sourcelinks = \
                            xml_helpers.handle_notes_with_brackets('word', name_to_id_map, expert_names_to_ids_map,
                                                                   term_sources_to_ids_map, lexeme_note_raw)

                        for note in lexeme_notes_with_sourcelinks:
                            word.lexemeNotes.append(note)
                            if note.value.startswith('KONTROLLIDA'):
                                word.lexemeTags.append('term kontrolli ilmikut')
                    elif xml_helpers.does_note_contain_ampersand_in_sourcelink(lexeme_note_raw):
                        lexeme_notes, concept_notes = xml_helpers.handle_ampersand_notes('word', lexeme_note_raw, term_sources_to_ids_map)
                        for note in lexeme_notes:
                            word.lexemeNotes.append(note)
                    else:
                        term_pairs = ['ÜMT/ÜAU', 'AKE/ALK', 'ELS/ETM', 'MRS/MST', 'PTE/PTH', 'IKS/IFH']

                        if any(char in lexeme_note_raw[:-50] for char in '[]{}'):
                            word.lexemeTags.append('term kontrolli ilmikut')
                            word.lexemeNotes.append(data_classes.Lexemenote(
                                value='KONTROLLIDA: ' + lexeme_note_raw,
                                lang='est',
                                publicity=False,
                                sourceLinks=None
                            ))
                        else:
                            pair_found = False
                            for pair in term_pairs:
                                if pair in lexeme_note_raw:
                                    lexemenotes, lexeme_tags = xml_helpers.handle_note_with_double_initials_in_term_level(
                                        lexeme_note_raw,
                                        term_sources_to_ids_map,
                                        expert_names_to_ids_map,
                                        name_to_id_map
                                    )
                                    for n in lexemenotes:
                                        word.lexemeNotes.append(n)
                                    for t in lexeme_tags:
                                        word.lexemeTags.append(t)
                                    pair_found = True
                                    break

                            if not pair_found:
                                lexeme_notes_with_sourcelinks, concept_notes_with_sourcelinks = xml_helpers.handle_notes_with_brackets(
                                    'word',
                                    name_to_id_map,
                                    expert_names_to_ids_map,
                                    term_sources_to_ids_map,
                                    lexeme_note_raw
                                )

                                for note in lexeme_notes_with_sourcelinks:
                                    if note.value.startswith('KONTROLLIDA'):
                                        word.lexemeTags.append('term kontrolli ilmikut')
                                    word.lexemeNotes.append(note)



            words.append(word)

    words = xml_helpers.update_notes(words)

    for word in words:
        count = sum(1 for w in words if w.lang == word.lang)
        word.lexemeValueStateCode = xml_helpers.parse_value_state_codes(word.lexemeValueStateCode, count)

        logger.info('Added word - word value: %s, word language: %s, word is public: %s, word type: %s, '
                    'word value state code: %s',
                    word.valuePrese, word.lang, word.lexemePublicity, word.wordTypeCodes, word.lexemeValueStateCode)
        if word.usages:
            logger.info('Added word usage: %s', str(word.usages))
        if word.lexemeNotes:
            logger.info('Added word notes: %s', str(word.lexemeNotes))

        word.lexemeNotes.sort(key=lambda x: x.publicity, reverse=True)

    xml_helpers.remove_lexeme_value_state_code(words)

    return words, definitions, notes


# Write aviation concepts, all other concepts and domains to separate JSON files
def print_concepts_to_json(concepts):
    logger.debug('Number of concepts: %s', str(len(concepts)))
    #logger.debug('Number of aviation concepts: %s', str(len(aviation_concepts)))

    output_folder = 'files/output'
    os.makedirs(output_folder, exist_ok=True)

    for concept_list, filename in [(concepts, 'concepts.json')]:

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


def transform_esterm_to_json(name_to_id_map, expert_names_to_ids_map, term_sources_to_ids_map):
# Opening the file, parsing, writing JSON files
    with open('files/input/esterm.xml', 'rb') as file:
        xml_content = file.read()

    parser = etree.XMLParser(encoding='UTF-16')
    root = etree.fromstring(xml_content, parser=parser)

    concepts = parse_mtf(root, name_to_id_map, expert_names_to_ids_map, term_sources_to_ids_map)

    print_concepts_to_json(concepts)

    logger.info('Finished transforming Esterm XML file to JSON files.')