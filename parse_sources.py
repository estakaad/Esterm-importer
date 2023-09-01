import re
from lxml import etree
import json
import xml_helpers
import log_config


logger = log_config.get_logger()

# Replace Esterm source attributes with their corresponding attributes in Ekilex
def get_mapping_value(key):

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

    return mapping.get(key)


# Replace Esterm source types with Ekilex source types
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
            obj['type'] = 'DOCUMENT'
        elif obj['type'] == 'Meediaväljaanne':
            obj['type'] = 'UNKNOWN'
        elif obj['type'] == 'Eesti õigusakt':
            obj['type'] = 'DOCUMENT'
        elif obj['type'] == 'EU õigusakt':
            obj['type'] = 'DOCUMENT'
        elif obj['type'] == 'EÜ õigusakt':
            obj['type'] = 'DOCUMENT'

    return json_objects


# Fetch values from XML elements and map them to JSON objects
def create_json(conceptGrp):
    logger.info('Creating source JSON object from XML.')
    json_object = {
        'type': '',
        'sourceProperties': []
    }

    type_descrip = conceptGrp.find('.//descrip[@type="Tüüp"]')
    if type_descrip is not None and type_descrip.text is not None:
        json_object['type'] = type_descrip.text

    for termGrp in conceptGrp.xpath('./languageGrp/termGrp'):
        term = termGrp.findtext('term')
        if term:
            json_object['sourceProperties'].append({
                'type': 'SOURCE_NAME',
                'valueText': term
            })
        for descrip in termGrp.xpath('.//descrip'):
            descrip_type = get_mapping_value(descrip.get('type'))
            if descrip_type:
                descrip_value = descrip.text if descrip.text is not None else ''
                original_type = descrip.get('type')
                # Handle types which are not present in Ekilex.
                # They are transformed as notes, but their original type is added to the note value
                if descrip_type == 'NOTE' and original_type != 'Märkus':
                    descrip_value = f"{original_type}: {descrip_value}"

                json_object['sourceProperties'].append({
                    'type': descrip_type,
                    'valueText': descrip_value
                })

    source_name_objects = []
    other_objects = []

    for obj in json_object["sourceProperties"]:
        if obj["type"] == "SOURCE_NAME":
            source_name_objects.append(obj)
        else:
            other_objects.append(obj)

    # Sort objects of type 'SOURCE_NAME' in ascending order by the length of the key value
    source_name_objects.sort(key=lambda obj: len(obj["valueText"]))

    json_object["sourceProperties"] = source_name_objects + other_objects

    logger.info(f'Finished creating JSON object from XML source. Source names: {source_name_objects}')

    return json_object


# Parse Esterm XML, filter out sources and transform them to JSON objects. Add expert sources.
# Return output/sources.json
def export_sources_from_xml(filename):
    logger.info('Started parsing XML for sources.')

    with open(filename, 'rb') as file:
        xml_content = file.read()

    parser = etree.XMLParser(encoding='UTF-16')
    root = etree.fromstring(xml_content, parser=parser)

    json_objects = []

    for conceptGrp in root.xpath('//conceptGrp'):
        type_of_concept = xml_helpers.type_of_concept(conceptGrp)

        if type_of_concept == 'source':
            # Map Esterm XML elements and their values to JSON objects suitable for Ekilex
            json_objects.append(create_json(conceptGrp))

    # Replace Esterm source types with Ekilex source types
    json_objects = replace_type(json_objects)

    # Write sources to sources.json
    with open('files/output/sources.json', 'w', encoding='utf-8') as file:
        json.dump(json_objects, file, indent=4, ensure_ascii=False)

    logger.info('Finished parsing XML for souces.')
    return file


# This is to be ran once all concepts are parsed, because until then the EKSPERT-type source sourcelinks are unknown
def find_expert_values(data):
    expert_values = set()
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str) and value.startswith("EKSPERT"):
                expert_values.add(value)
            elif isinstance(value, (dict, list)):
                expert_values.update(find_expert_values(value))
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                expert_values.update(find_expert_values(item))
    return list(expert_values)


def create_experts_objects_file(filename):
    json_objects = []

    with open(filename, 'r', encoding='utf-8') as f:
        for line in f.readlines():
            if line.startswith('EKSPERT '):
                name = line[8:].strip()
                json_object = {
                    "type": "PERSON",
                    "sourceProperties": [
                        {
                            "type": "SOURCE_NAME",
                            "valueText": name
                        }
                    ]
                }
                json_objects.append(json_object)

    with open('files/experts.json', 'w', encoding='utf-8') as f:
        json.dump(json_objects, f, ensure_ascii=False, indent=4)

    return f