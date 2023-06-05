from lxml import etree
import json
import re
import xml_helpers
from typing import List, Optional
from dataclasses import dataclass, field
import os

@dataclass
class Domain:
    value: str

@dataclass
class Definition:
    value: str
    lang: str
    definitionTypeCode: str
    source: str

@dataclass
class Note:
    value: str
    lang: str
    is_public: int

@dataclass
class Forum:
    value: str

@dataclass
class Usage:
    value: str
    is_public: int

@dataclass
class Word:
    value: str
    lang: str
    is_public: int
    word_type: Optional[str] = None
    value_state_code: Optional[str] = None
    usage: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

@dataclass
class Concept:
    domains: list = field(default_factory=list)
    definitions: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    forum: list = field(default_factory=list)
    words: list = field(default_factory=list)


# Parse the whole Esterm XML and return aviation concepts, all other concepts and the sources of the concepts
def parse_mtf(root):
    concepts = []
    sources = []
    aviation_concepts = []

    for conceptGrp in root.xpath('/mtf/conceptGrp'):
        concept = Concept()

        # Decide whether the concept will be added to the general list of concepts, list of aviation concepts or
        # list of sources
        if conceptGrp.xpath('languageGrp/language[@type="Allikas"]'):
            list_to_append = sources
        elif xml_helpers.is_concept_aviation_related(conceptGrp):
            list_to_append = aviation_concepts
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
                        concept.domains.append(Domain(domain))
            # Get concept notes and add to the list of concept notes.
            elif descrip_element.get('type') == 'Märkus':
                concept.notes.append(Note(
                    value=descrip_element_value,
                    lang='est',
                    is_public=1
                ))
            # Get concept tööleht and add its value to concept forum list.
            elif descrip_element.get('type') == 'Tööleht':
                concept.forum.append(Forum(
                    value=descrip_element_value
                ))
            # Get concept context and add its value to the concept usage list
            elif descrip_element.get('type') == 'Kontekst':
                concept.usage.append(Usage(
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

            word = Word(
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

                if descrip_type == 'Keelenditüüp':

                    # Kui keelenditüüp on 'eelistermin' ja languageGrp element sisaldab rohkem kui üht termGrp elementi,
                    # tuleb Ekilexis väärtusoleku väärtuseks salvestada 'eelistatud'
                    if descrip_text == 'eelistermin' and len(termGrps) > 1:
                        word.value_state_code = 'eelistatud'
                    # Kui keelenditüüp on 'lühend', tuleb Ekilexis keelenditüübi väärtuseks salvestada 'lühend'
                    elif descrip_text == 'lühend':
                        word.word_type = 'l'
                    # Kui keelenditüüp on 'sünonüüm' ja termin on kohanimi, tuleb Ekilexis väärtusolekuks
                    # salvestada 'mööndav'. Kui keelenditüüp on 'sünonüüm' ja termin ei ole kohanimi, siis Ekilexis ?
                    elif descrip_text == 'sünonüüm':
                        word.value_state_code = 'mööndav'
                    # Kui keelenditüüp on 'variant', siis Ekilexis väärtusolekut ega keelenditüüpi ei salvestata.
                    elif descrip_text == 'variant':
                        word.value_state_code = None
                    # Kui keelenditüüp on 'endine', tuleb Ekilexis väärtusoleku väärtuseks salvestada 'endine'
                    elif descrip_text == 'endine':
                        word.value_state_code = 'endine'
                    # Kui keelenditüüp on 'väldi', tuleb Ekilexis väärtusoleku väärtuseks salvestada 'väldi'
                    elif descrip_text == 'väldi':
                        word.value_state_code = 'väldi'

                if descrip_type == 'Märkus':
                    if descrip_text.startswith(('SÜNONÜÜM: ', 'ENDINE: ', 'VARIANT: ')):
                        # Add the note to the words with 'mööndav' or 'endine' value_state_codes
                        if 'SÜNONÜÜM: ' in descrip_text and 'mööndav' in words:
                            words['mööndav'].notes.append(descrip_text)
                        elif 'ENDINE: ' in descrip_text and 'endine' in words:
                            words['endine'].notes.append(descrip_text)
                    else:
                        word.notes.append(descrip_text)


            for descripGrp in termGrp.xpath('descripGrp'):
                descrip_type = descripGrp.xpath('descrip/@type')[0]
                descrip_text = descripGrp.xpath('descrip')[0].text
                # Kui /mtf/conceptGrp/languageGrp/termGrp/descripGrp/descrip[@type="Märkus"] alguses on
                # 'SÜNONÜÜM: ', 'VARIANT: ' või 'ENDINE: ', siis tuleb see salvestada selle termGrp
                # elemendi märkuseks, mille keelenditüüp Estermis on 'SÜNONÜÜM', 'VARIANT' või 'ENDINE'
                if descrip_type == 'Märkus':
                    word.notes.append(descrip_text)
                elif descrip_type == 'Kontekst':
                    word.usage.append(descrip_text)
                elif descrip_type == 'Allikas':
                    print('Allikas')
                elif descrip_type == 'Definitsioon':
                    definition_text = descrip_text.strip() if descrip_text is not None else 'testing'
                    if descripGrp.xpath('descrip/xref'):
                        source = descripGrp.xpath('descrip/xref')[0].text
                    else:
                        source = 'Testallikas'
                    definitions.append(Definition(
                        value=descrip_text.split('[')[0].strip(),
                        lang=xml_helpers.match_language(lang) if lang is not None else 'testing',
                        definitionTypeCode='definitsioon',
                        source=source
                    ))

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