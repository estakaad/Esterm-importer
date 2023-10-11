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
        'public': 'true',
        'sourceProperties': []
    }
    id = conceptGrp.find('concept').text

    type_descrip = conceptGrp.find('.//descrip[@type="Tüüp"]')
    if type_descrip is not None and type_descrip.text is not None:
        json_object['type'] = type_descrip.text

    for termGrp in conceptGrp.xpath('./languageGrp/termGrp'):
        term = termGrp.findtext('term')
        full_title_note = None

        if term:
            if term.endswith('...'):
                for descrip in termGrp.xpath('.//descrip[@type="Märkus"]'):
                    descrip_text = descrip.text
                    if descrip_text:
                        if 'Täispealkiri: ' in descrip_text:
                            full_title_note = descrip_text.split('Täispealkiri: ')[1]
                            term = full_title_note  # Add full title to term
                            break
                        if 'täispealkiri: ' in descrip_text:
                            full_title_note = descrip_text.split('täispealkiri: ')[1]
                            term = full_title_note  # Add full title to term
                            break
                        elif descrip_text.startswith('...'):
                            full_title_note = descrip_text
                            term = term.strip('...')
                            term += descrip_text.strip('... ')
                            break
            else:
                for descrip in termGrp.xpath('.//descrip[@type="Märkus"]'):
                    descrip_text = descrip.text
                    if descrip_text:
                        if 'Täispealkiri: ' in descrip_text:
                            full_title_note = descrip_text.split('Täispealkiri: ')[1]
                            term = full_title_note
                            break
                        elif 'täispealkiri: ' in descrip_text:
                            full_title_note = descrip_text.split('täispealkiri: ')[1]
                            term = full_title_note
                            break

            json_object['sourceProperties'].append({
                'type': 'SOURCE_NAME',
                'valueText': term
            })

        for descrip in termGrp.xpath('.//descrip'):
            descrip_type = get_mapping_value(descrip.get('type'))
            if descrip_type:

                descrip_value = descrip.text if descrip.text is not None else ''
                original_type = descrip.get('type')

                # Update 'Märkus' if full title was extracted
                if descrip_type == 'NOTE' and full_title_note:
                    if full_title_note in descrip_value:
                        descrip_value = descrip_value.replace(full_title_note, '').strip()
                        descrip_value = descrip_value.replace('Täispealkiri:', '').strip().strip(';')
                        descrip_value = descrip_value.replace('täispealkiri:', '').strip().strip(';')

                # Handle types which are not present in Ekilex.
                # They are transformed as notes, but their original type is added to the note value
                if descrip_type == 'NOTE' and original_type != 'Märkus':
                    descrip_value = f"{original_type}: {descrip_value}"

                if not (descrip_type == 'NOTE' and descrip_value == ''):
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

    json_object["sourceProperties"].append({
                        'type': 'SOURCE_FILE',
                        'valueText': 'esterm.xml'
                    })
    json_object["sourceProperties"].append({
                        'type': 'EXTERNAL_SOURCE_ID',
                        'valueText': id
                    })

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