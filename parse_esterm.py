from lxml import etree
import json
import re
import xml_helpers
from typing import List, Optional
from dataclasses import dataclass, field
import uuid

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
    word_type: str
    value_state_code: Optional[str] = None
    usage: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

@dataclass
class Concept:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    domains: list = field(default_factory=list)
    definitions: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    forum: list = field(default_factory=list)
    words: list = field(default_factory=list)


def parse_mtf(root):
    concepts = []
    sources = []
    aviation_concepts = []
    added_concepts_ids = set()

    for conceptGrp in root.xpath('/mtf/conceptGrp'):
        concept = Concept()

        if concept.id in added_concepts_ids:
            print(f"Concept with id {concept.id} is already added!")
            continue

        if conceptGrp.xpath("languageGrp/language[@type='Allikas']"):
            list_to_append = sources
        elif xml_helpers.is_concept_aviation_related(conceptGrp):
            list_to_append = aviation_concepts
        else:
            list_to_append = concepts

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

            termGrps = languageGrp.xpath('termGrp')

            for termGrp in termGrps:
                term = termGrp.xpath('term')[0].text if termGrp.xpath('term') else 'testing'
                if termGrp.xpath('descripGrp/descrip[@type="Keelenditüüp"]'):
                    term_text = termGrp.xpath('descripGrp/descrip[@type="Keelenditüüp"]')[0].text
                    value_state_code = None
                    if term_text == 'eelistermin' and len(termGrps) > 1:
                        value_state_code = 'eelistatud'
                    elif term_text == 'sünonüüm':
                        value_state_code = 'mööndav'
                    elif term_text == 'variant':
                        value_state_code = 'variant - seda ignoreerime'
                    elif term_text == 'endine':
                        value_state_code = 'endine'
                    elif term_text == 'väldi':
                        value_state_code = 'väldi'
                else:
                    value_state_code = 'testing - vist pole väärtust'

                word = Word(
                    value=term,
                    lang=xml_helpers.match_language(lang),
                    is_public=1,
                    word_type='testing',
                    value_state_code=value_state_code
                )

                for descripGrp in termGrp.xpath('descripGrp'):
                    descrip_type = descripGrp.xpath('descrip/@type')[0]
                    descrip_text = descripGrp.xpath('descrip')[0].text
                    if descrip_type == 'Märkus':
                        word.notes.append(descrip_text)
                    elif descrip_type == 'Kontekst':
                        word.usage.append(descrip_text)
                    elif descrip_type == 'Allikas':
                        print('allikas')
                    elif descrip_type == 'Definitsioon':
                        definition_text = descrip_text.strip() if descrip_text is not None else 'testing'
                        if descripGrp.xpath('descrip/xref'):
                            source = descripGrp.xpath('descrip/xref')[0].text
                        else:
                            source = 'testallikas'
                        concept.definitions.append(Definition(
                            value=descrip_text.split('[')[0].strip(),
                            lang=xml_helpers.match_language(lang) if lang is not None else 'testing',
                            definitionTypeCode='definitsioon',
                            source=source
                        ))

                concept.words.append(word)

        list_to_append.append(concept)

        added_concepts_ids.add(concept.id)

    return concepts, sources, aviation_concepts


def print_concepts_to_json(concepts, sources, aviation_concepts):
    print(str(len(concepts)))
    print(str(len(sources)))
    print(str(len(aviation_concepts)))
    for concept_list, filename in [(concepts, 'concepts.json'),
                                   (sources, 'sources.json'),
                                   (aviation_concepts, 'aviation_concepts.json')]:
        concepts_json = json.dumps(
            [concept.__dict__ for concept in concept_list],
            default=lambda o: o.__dict__,
            indent=4,
            ensure_ascii=False
        )
        with open(filename, 'w', encoding='utf8') as json_file:
            json_file.write(concepts_json)


def read_xml_file(file_path):
    with open(file_path, 'rb') as file:
        xml_content = file.read().decode('utf-8', errors='ignore')
    xml_content = re.sub('\<\?xml.*\?\>', '', xml_content)
    return xml_content

with open('esterm.xml', 'rb') as file:
    xml_content = file.read()

parser = etree.XMLParser(encoding='UTF-16')
root = etree.fromstring(xml_content, parser=parser)

concepts, sources, aviation_concepts = parse_mtf(root)
print_concepts_to_json(concepts, sources, aviation_concepts)