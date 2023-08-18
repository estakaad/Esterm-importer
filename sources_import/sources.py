from lxml import etree
import json
import concepts_import
from concepts_import import xml_helpers

mapping = {
    'CELEX': 'SOURCE_CELEX',
    'WWW': 'SOURCE_WWW',
    'Ilmumisaasta': 'SOURCE_PUBLICATION_YEAR',
    'Väljaande nimi, nr': 'SOURCE_PUBLICATION_NAME',
    'Märkus': 'NOTE',
    'RT': 'SOURCE_RT',
    'Päritolu': 'SOURCE_EXPLANATION',
    'Autor': 'SOURCE_AUTHOR',
    'Kirjastus': 'SOURCE_PUBLISHER',
    'ISBN': 'SOURCE_ISBN',
    'Ilmumiskoht': 'SOURCE_PUBLICATION_PLACE',
    'Artikli autor': 'SOURCE_ARTICLE_AUTHOR',
    'Aktiliik': 'NOTE',
    'Aktinumber': 'NOTE',
    'Akti vastuvõtja': 'NOTE',
    'Vastuvõtukuupäev': 'NOTE',
    'ISSN': 'SOURCE_ISSN'
}


def create_json(conceptGrp):
    json_object = {
        'type': '',
        'sourceProperties': []
    }

    tyyp_descrip = conceptGrp.find('.//descrip[@type="Tüüp"]')
    if tyyp_descrip is not None and tyyp_descrip.text is not None:
        json_object['type'] = tyyp_descrip.text

    for termGrp in conceptGrp.xpath('./languageGrp/termGrp'):
        term = termGrp.findtext('term')
        if term:
            json_object['sourceProperties'].append({
                'type': 'SOURCE_NAME',
                'valueText': term
            })
        for descrip in termGrp.xpath('.//descrip'):
            descrip_type = mapping.get(descrip.get('type'))
            if descrip_type:
                descrip_value = descrip.text if descrip.text is not None else ''
                original_type = descrip.get('type')
                if descrip_type == 'NOTE' and original_type != 'Märkus':
                    descrip_value = f"{original_type}: {descrip_value}"
                json_object['sourceProperties'].append({
                    'type': descrip_type,
                    'valueText': descrip_value,
                    'valueDate': None
                })

    return json_object


def process_xml_file(filename):
    with open(filename, 'rb') as file:
        xml_content = file.read()

    parser = etree.XMLParser(encoding='UTF-16')
    root = etree.fromstring(xml_content, parser=parser)

    json_objects = []

    for conceptGrp in root.xpath('//conceptGrp'):
        type_of_concept = concepts_import.xml_helpers.type_of_concept(conceptGrp)

        if type_of_concept == 'source':
            json_objects.append(create_json(conceptGrp))

    return json_objects


def replace_type(json_objects):
    for obj in json_objects:
        if obj['type'] == '':
            obj['type'] = 'UNKNOWN'
        elif obj['type'] == 'Muu':
            obj['type'] = 'UNKNOWN'
        elif obj['type'] == 'Konventsioon':
            obj['type'] = 'DOCUMENT'
        elif obj['type'] == 'Internet':
            obj['type'] = 'UNKNOWN'
        elif obj['type'] == 'Raamat':
            obj['type'] = 'UNKNOWN'
        elif obj['type'] == 'Meediaväljaanne':
            obj['type'] = 'UNKNOWN'
        elif obj['type'] == 'Eesti õigusakt':
            obj['type'] = 'DOCUMENT'
        elif obj['type'] == 'EU õigusakt':
            obj['type'] = 'DOCUMENT'
        elif obj['type'] == 'EÜ õigusakt':
            obj['type'] = 'DOCUMENT'

    return json_objects


def export_sources_from_xml(filepath):
    json_objects = process_xml_file(filepath)
    json_objects = replace_type(json_objects)
    with open('files/output/sources.json', 'w', encoding='utf-8') as file:
        json.dump(json_objects, file, indent=4, ensure_ascii=False)

    return file