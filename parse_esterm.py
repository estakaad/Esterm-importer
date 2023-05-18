from lxml import etree
from dataclasses import dataclass, field
import json
import re
import xml_helpers

from dataclasses import dataclass, field

@dataclass
class Domain:
    value: str

@dataclass
class Definition:
    value: str
    lang: str
    definitionTypeCode: str

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
    value_state_code: str
    is_public: int
    word_type: str
    usage: list = field(default_factory=list)  # Added usage field
    notes: list = field(default_factory=list)  # Added notes field

@dataclass
class Concept:
    domains: list = field(default_factory=list)
    definitions: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    forum: list = field(default_factory=list)
    words: list = field(default_factory=list)

def parse_mtf(xml_data):
    root = etree.fromstring(xml_data)
    concepts = []
    for conceptGrp in root.xpath('/mtf/conceptGrp'):
        concept = Concept()
        for descrip in conceptGrp.xpath('descripGrp/descrip'):
            descrip_text = etree.tostring(descrip, encoding="unicode", method="text") if descrip.text is not None else 'testing'
            if descrip.get('type') == 'Valdkonnaviide':
                for valdkonnaviide in descrip_text.split(';'):
                    valdkonnaviide = valdkonnaviide.strip()
                    if valdkonnaviide:
                        concept.domains.append(Domain(valdkonnaviide))

            elif descrip.get('type') == 'Märkus':
                concept.notes.append(Note(
                    value=descrip_text,
                    lang='est',
                    is_public=1
                ))
            elif descrip.get('type') == 'Tööleht':
                concept.forum.append(Forum(
                    value=descrip_text
                ))
            elif descrip.get('type') == 'Kontekst':
                concept.usage.append(Usage(
                    value=descrip_text,
                    is_public=1
                ))

        for languageGrp in conceptGrp.xpath('languageGrp'):
            lang = languageGrp.xpath('language')[0].get('lang') if languageGrp.xpath('language') else 'testing'

            for termGrp in languageGrp.xpath('termGrp'):
                term = termGrp.xpath('term')[0].text if termGrp.xpath('term') else 'testing'
                value_state_code = termGrp.xpath('descripGrp/descrip[@type="Keelenditüüp"]')[0].text \
                    if termGrp.xpath('descripGrp/descrip[@type="Keelenditüüp"]') else 'testing'
                word = Word(
                    value=term,
                    lang=xml_helpers.match_language(lang),
                    value_state_code=value_state_code,
                    is_public=1,
                    word_type='testing'
                )
                for descripGrp in termGrp.xpath('descripGrp'):
                    descrip_type = descripGrp.xpath('descrip/@type')[0]
                    descrip_text = descripGrp.xpath('descrip')[0].text
                    if descrip_type == 'Märkus':
                        word.notes.append(descrip_text)
                    elif descrip_type == 'Kontekst':
                        word.usage.append(descrip_text)
                    elif descrip_type == 'Definitsioon':
                        definition_text = descrip_text.strip() if descrip_text is not None else 'testing'
                        concept.definitions.append(Definition(
                            value=definition_text,
                            lang=lang if lang is not None else 'testing',
                            definitionTypeCode='definitsioon'
                        ))
                concept.words.append(word)

        concepts.append(concept)
    return concepts



def print_concepts_to_json(concepts):
    concepts_json = json.dumps([concept.__dict__ for concept in concepts], default=lambda o: o.__dict__, indent=4, ensure_ascii=False)
    #print(concepts_json)
    with open('concepts.json', 'w', encoding='utf8') as json_file:
        json_file.write(concepts_json)

def read_xml_file(file_path):
    with open(file_path, 'rb') as file:
        xml_content = file.read().decode('utf-8', errors='ignore')
    # Remove encoding declaration
    xml_content = re.sub('\<\?xml.*\?\>', '', xml_content)
    return xml_content

xml_data = read_xml_file('test.xml')
concepts = parse_mtf(xml_data)
print_concepts_to_json(concepts)