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
def export_sources_from_xml(filename, expert_sources):
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

    json_objects.append(expert_sources)

    # Write sources to sources.json
    with open('files/output/sources.json', 'w', encoding='utf-8') as file:
        json.dump(json_objects, file, indent=4, ensure_ascii=False)

    logger.info('Finished parsing XML for souces.')
    return file


def export_experts_names_from_xml(filename):
    logger.debug('Started parsing experts.')

    with open(filename, 'rb') as file:
        xml_content = file.read()

    parser = etree.XMLParser(encoding='UTF-16')
    root = etree.fromstring(xml_content, parser=parser)

    # Convert the entire XML tree to a string
    xml_as_string = etree.tostring(root, encoding='unicode')

    # Match "EKSPERT" and everything up to the next closing tag
    matches = re.findall(r'EKSPERT[^<]*<[^<]*>[^<]*', xml_as_string)

    # Use a set to store unique results
    unique_matches = set()

    for match in matches:

        # Remove any XML tags to leave just the text content
        cleaned_match = re.sub(r'<.*?>', '', match)
        cleaned_match = re.sub(r'EKSPERT\">EKSPERT\s', '', cleaned_match)
        cleaned_match = re.sub(r'EKSPERT\s*\{', '', cleaned_match)
        cleaned_match = re.sub(r'\}.*', '', cleaned_match)
        cleaned_match = re.sub(r'\].*', '', cleaned_match)
        cleaned_match = re.sub(r'\;.*', '', cleaned_match)
        cleaned_match = re.sub(r'\">\s', '', cleaned_match)
        cleaned_match = re.sub(r'.*>', '', cleaned_match)
        cleaned_match = re.sub(r'{', '', cleaned_match)
        cleaned_match = re.sub(r'\n.*', '', cleaned_match)
        cleaned_match = re.sub(r',.*', '', cleaned_match)


        cleaned_match = cleaned_match.strip()
        cleaned_match = cleaned_match.replace('EKSPERT ', '')

        if cleaned_match.startswith('EKSPERT!'):
            continue
        if cleaned_match.isdigit():
            continue
        if cleaned_match.startswith('Kalle Truusi keemia'):
            continue
        if 'keemiaterminite tabel' in cleaned_match:
            continue

        unique_matches.add(cleaned_match)

    strings_to_be_removed = ['32009D0450',
                             'LLT AS-järgi vananenud termin. [SES',
                             'Gerd Laubile [MVS',
                             'EKSPERTVilju Lilleleht',
                             'Meili Rei soovituse põhjal KAN 1.11.2001',
                             'Heve Kirikal seda ei kinnita: "Kaubatundja mõistet täna enam kaubandusettevõttes '
                             'ei kasutata ja tõepoolest tahetakse kasutada selle asemel mechandiser. Kahtlemata '
                             'on selle sisu ka muutunud',
                             'Heve Kirikal vaste sobivust ei kinnita. "Merchandising" enamasti tõlgitud kui kaubandus',
                             'Viljar Peep). Tinglikult on EN termini allikaks kirjes Pille Vinkel',
                             'Kalle Truus: eelistermin ja lühend ei ole võrreldavad terminid. NADP ei ole dinaatriumsoola lühend (tekstist on valesti aru saadud).',
                             'Kalle Truusi keeemiaterminite tabel [SES 05.11.2015',
                             'Endel Risthein (3.11.2017): Tripping current - Eesti standardikeskuses on kokku lepitud',
                             'Lauri Kreen: spetsiifiliste lennutegevuste riskihindamine. Alternatiivtõlked: spetsiifiliste operatsioonide',
                             'Lauri Kreen: eelnevalt määratletud (lennutegevuste) riskihindamine. Alternatiivtõlked: eelmääratletud',
                             'Mihkel Kaljurand: USA organisats.',
                             'Andreas Kangur andis heakskiidu eestikeelsele plokile',
                             'Rain Veetõusme: 1. Press release vaste peaks olema pressiteade. 2. Pressiteade '
                             'ja pressiavaldus. Nende erinevus pole suur',
                             'Sven Nurk (MKM): Liiklusseaduses on võetud kasutusele termin maastikusõiduk '
                             'puhtalt selle pärast',
                             'EKSPERT: Teoreetilised veeliinid määratakse arvutuste põhjal ja kantakse joonisele. [ETM 26.10.2005',
                             'EKSPERT: Turvalisuse all mõeldakse laeva',
                             'Aare Tuvi sõnul ei ole EL-i õigusaktides "special fishing permit" enam kasutusel.'
                             ' Nüüd on "fishing authorisation"',
                             'Lauri Luht: "Terminit „elektrooniline turvalisus“ kasutab HOS',
                             'Sven Nurk soovitab ELi määruse eeskujul vastet "self-balancing vehicle". 6. Algul arvasin',
                             'EKSPERT: Eesti raudteesüsteemis rööpamurdusid eraldi ei klassifitseerita. Pidasin nõu '
                             'rööbasteede remondi ja ehitusega tegeleva spetsialistiga ja tema vastu oli lihtne - '
                             '"meie oleme lihtne rahvas ja ei erista rööpamurdusid nende tekke järgi. Kui on murd',
                             'Kalle Truus ET vaste kohta: mitte ülaltoodud kontekstis',
                             'Jaan Ginter 20.01.2020: Praegu ESTERM-is olev kirje ei ole hea kui eesmärgiks on selle '
                             'terminibaasi kasutamine ka inglisekeelsest tekstist eesti keelde tõlkimisel. '
                             'See kirje tuleneb praegusest KarS § 116 sõnastusest',
                             'Priit Kask). 2. Paljudes allikates käsitletakse sünonüümidena (üks AmE',
                             'Siiri Auliku ettepanekul kustutatud väldi termin "damage to property" ja märkus '
                             '""damage to property" ei ole vale',
                             'Madli Vitismann: "Tõenäoliselt teeb merekeele nõukoda ettepaneku seaduse järgmistes '
                             'versioonides "reisiparvlaeva" mitte kasutada ja piirduda "parvlaevaga"." [SES 30.05.2016',
                             'on siin tinglik: tegelikult on definitsiooni taga rohkem inimesi Lennuliiklusteeninduse '
                             'AS-st. 2. KIRJE POOLELI. KÜSIMUSED! 8.01.18 kiri eksperdile (Teele Kohv',
                             'Kalle Truusi sõnul on selle jaoks teine termin. Eestikeelsete vastetena pakub ta välja '
                             '"pundunud (või punnutatud) polüstüreen" [SES 10.11.2014',
                             'Toomas Paalme pakkus välja termini "harjaspiir"',
                             'Kalle Truus on sellesse kirjesse teinud mitu parandust ja lõpuks kirjutanud ET termini '
                             'kohta: üksi ei ole seda terminit mõtet kasutada. TERMIUMis ei esine',
                             'Kalle Truusi järgi on "aatomite arvuline suhe" liiga kohmakas ja ta pakub selle asemele '
                             '"aatomsuhe". Mitme ELi direktiivi (nt 32014R0136',
                             'Heve Kirikal seda ei kinnita: ""Kaubatundja mõistet täna enam kaubandusettevõttes ei '
                             'kasutata ja tõepoolest tahetakse kasutada selle asemel mechandiser. Kahtlemata on selle sisu ka muutunud',
                             'Madli Vitismann: "ro-ro" (roll-on-roll-off) ei ole laevatüüp',
                             'Peep Christjanson) tundub laiem mõiste (eesti keeles näib sellele vastavat "poorne kummi"'

                             ]

    for string in strings_to_be_removed:
        unique_matches.remove(string)
    logger.debug('Finished parsing experts.')
    return unique_matches


def create_expert_sources(expert_names):

    expert_sources = []

    for name in expert_names:
        expert_source = {
                            "type": "PERSON",
                            "sourceProperties": [
                                {
                                    "type": "SOURCE_NAME",
                                    "valueText": name
                                }
                            ]
                        }
        expert_sources.append(expert_source)
        logger.info(f'Created source object for expert with name {name}')

    return expert_sources