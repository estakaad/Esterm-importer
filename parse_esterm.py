from lxml import etree
import json
import re
import xml_helpers
from typing import List, Optional
from dataclasses import dataclass, field
import os
import data_classes

# @dataclass
# class Domain:
#     value: str
#
# @dataclass
# class Definition:
#     value: str
#     lang: str
#     definitionTypeCode: str
#     source: str
#
# @dataclass
# class Note:
#     value: str
#     lang: str
#     is_public: int
#
# @dataclass
# class Forum:
#     value: str
#
# @dataclass
# class Usage:
#     value: str
#     is_public: int
#
# @dataclass
# class Word:
#     value: str
#     lang: str
#     is_public: int
#     word_type: Optional[str] = None
#     value_state_code: Optional[str] = None
#     usage: List[str] = field(default_factory=list)
#     notes: List[str] = field(default_factory=list)
#
# @dataclass
# class Concept:
#     domains: list = field(default_factory=list)
#     definitions: list = field(default_factory=list)
#     notes: list = field(default_factory=list)
#     forum: list = field(default_factory=list)
#     words: list = field(default_factory=list)


# Parse the whole Esterm XML and return aviation concepts, all other concepts and the sources of the concepts
def parse_mtf(root):
    concepts = []
    sources = []
    aviation_concepts = []

    for conceptGrp in root.xpath('/mtf/conceptGrp'):
        concept = data_classes.Concept()

        if xml_helpers.type_of_concept(conceptGrp) == 'source':
            list_to_append = sources
        elif xml_helpers.type_of_concept(conceptGrp) == 'aviation':
            list_to_append = aviation_concepts
        elif xml_helpers.type_of_concept(conceptGrp) == 'general':
            list_to_append = concepts
        else:
            list_to_append = concepts

        # Parse concept level descrip elements and add their values as attributes to Concept
        for descrip_element in conceptGrp.xpath('descripGrp/descrip'):

            descrip_element_value = etree.tostring(descrip_element, encoding='unicode', method='text')

            # Get concept domain and add to the list of concept domains
            if descrip_element.get('type') == 'Valdkonnaviide':
                for domain in descrip_element_value.split(';'):
                    domain = domain.strip()
                    if domain:
                        concept.domains.append(data_classes.Domain(domain))
            # Get concept notes and add to the list of concept notes.
            elif descrip_element.get('type') == 'Märkus':
                concept.notes.append(data_classes.Note(
                    value=descrip_element_value,
                    lang='est',
                    is_public=1
                ))
            # Get concept tööleht and add its value to concept forum list.
            elif descrip_element.get('type') == 'Tööleht':
                concept.forum.append(data_classes.Forum(
                    value=descrip_element_value
                ))
            # Get concept context and add its value to the concept usage list
            elif descrip_element.get('type') == 'Kontekst':
                concept.usage.append(data_classes.Usage(
                    value=descrip_element_value,
                    is_public=1
                ))

        # Concept level data is parsed, now to parsing word (term) level data
        words, definitions = parse_words(conceptGrp, concept)

        for word in words:
            concept.words.append(word)

        for definition in definitions:
            concept.definitions.append(definition)

        list_to_append.append(concept)

    return concepts, sources, aviation_concepts


# Parse word elements in one concept in XML
def parse_words(conceptGrp, concept):

    words = []
    definitions = []

    for languageGrp in conceptGrp.xpath('languageGrp'):

        termGrps = languageGrp.xpath('termGrp')

        for termGrp in termGrps:

            word = data_classes.Word(
                value='term',
                lang='est',
                is_public=True)

            # Get word (term) language and assign as attribute lang
            lang = languageGrp.xpath('language')[0].get('lang')
            word.lang = xml_helpers.match_language(lang)
            word.value = termGrp.xpath('term')[0].text

            # Parse descripGrp elements of languageGrp element
            for descripGrp in termGrp.xpath('descripGrp'):
                descrip_type = descripGrp.xpath('descrip/@type')[0]
                descrip_text = descripGrp.xpath('descrip')[0].text

                # Parse word type as value state code or word type
                if descrip_type == 'Keelenditüüp':

                    if xml_helpers.is_type_word_type(descrip_text):
                        word.word_type = xml_helpers.parse_word_types(descrip_text)
                    else:
                        word.value_state_code = xml_helpers.parse_value_state_codes(descrip_text, termGrps)

                if descrip_type == 'Definitsioon':
                    definitions.append(xml_helpers.parse_definition(descrip_text,descripGrp, lang))
                #     if descripGrp.xpath('descrip/xref'):
                #         source = descripGrp.xpath('descrip/xref')[0].text
                #     else:
                #         source = 'Testallikas'
                #     definitions.append(Definition(
                #         value=descrip_text.split('[')[0].strip(),
                #         lang=xml_helpers.match_language(lang) if lang is not None else 'testing',
                #         definitionTypeCode='definitsioon',
                #         source=source
                #     ))

                if descrip_type == 'Kontekst':
                    word.usage.append(descrip_text)

                if descrip_type == 'Allikas':
                    print('Allikas')

                if descrip_type == 'Märkus':
                    word.notes.append(descrip_text)

            words.append(word)

    return words, definitions


# Write aviation concepts, all other concepts and sources of the concepts to three separate JSON files
def print_concepts_to_json(concepts, sources, aviation_concepts):
    print(str(len(concepts)))
    print(str(len(sources)))
    print(str(len(aviation_concepts)))
    output_folder = 'output'
    os.makedirs(output_folder, exist_ok=True)

    for concept_list, filename in [(concepts, 'concepts.json'),
                                   (sources, 'sources.json'),
                                   (aviation_concepts, 'aviation_concepts.json')]:
        concepts_json = json.dumps(
            [concept.__dict__ for concept in concept_list],
            default=lambda o: o.__dict__,
            indent=4,
            ensure_ascii=False
        )
        with open(os.path.join(output_folder, filename), 'w', encoding='utf8') as json_file:
            json_file.write(concepts_json)


def transform_esterm_to_json():
# Opening the file, parsing, writing JSON files
    with open('input/esterm.xml', 'rb') as file:
        xml_content = file.read()

    parser = etree.XMLParser(encoding='UTF-16')
    root = etree.fromstring(xml_content, parser=parser)

    concepts, sources, aviation_concepts = parse_mtf(root)
    print_concepts_to_json(concepts, sources, aviation_concepts)