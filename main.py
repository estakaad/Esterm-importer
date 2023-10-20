import expert_sources_helpers
import parse_concepts
import parse_sources
import requests_concepts
import requests_sources
import json
import log_config
import xml_helpers

logger = log_config.get_logger()

esterm_filename = 'files/input/esterm.xml'

# 1. Compile JSON with expert sources. Contains
# - EKSPERT, PÄRING, CONSILIUM, DELEST, DGT, PARLAMENT type sources from esterm.xml
# - metadata from eksperdid.xlsx
# # #
input_excel = 'files/input/ekspertide_lisainfo.xlsx'
output_json = 'files/output/sources/eksperdid.json'
expert_info_from_esterm = 'files/input/eksperdid_estermist.csv'
expert_info_for_api_calls = 'files/output/sources/expert_sources.json'

expert_sources_helpers.excel_to_json(input_excel, output_json)
expert_sources_helpers.create_experts_sources(output_json, expert_info_from_esterm, expert_info_for_api_calls)

# 2. Export sources from XML input/esterm.xml.
# Returns sources files/output/sources/sources.json
#file = parse_sources.export_sources_from_xml(esterm_filename)

# 3. Get ID-s of existing sources. If source doesn't exist yet, create it and get its ID.
# Add the sources with their ID-s to file output/sources/sources_with_ids.json
# Add ID-s of created sources to files/output/sources//ids_of_created_sources.json
# Return file output/sources/sources_with_ids.json
#
#sources_output_json_filename = 'files/output/sources/sources.json'
#updated_sources_file = requests_sources.assign_ids_to_all_sources(sources_output_json_filename)

# 4. Add expert sources. No need to check if it exists, because we know they don't.
# Add IDs to files/output/sources/expert_sources.json
# TODO
# Until then, use dummy ID 60180.
#
# # # 5. Map source names to their ID-s
#with open('files/output/sources/sources_with_ids-testimiseks.json', 'r', encoding='utf-8') as f:
#     updated_sources = json.load(f)

#name_to_id_map = xml_helpers.create_name_to_id_mapping(updated_sources)

#with open('files/output/sources/expert_sources.json', 'r', encoding='utf-8') as f:
#     expert_sources = json.load(f)

#expert_names_to_ids_map = expert_sources_helpers.create_name_and_type_to_id_mapping_for_expert_sources(expert_sources)
#
# # 6. Export concepts from XML. Returns files/output/concepts.json and files/output/aviation_concepts.json
#parse_concepts.transform_esterm_to_json(name_to_id_map, expert_names_to_ids_map)

# 7. Check if word exists. If it does, add its ID
#requests_concepts.update_word_ids('files/output/concepts.json', 'eki')
#requests_concepts.update_word_ids('files/output/aviation_concepts.json', 'eki')

# 8. Import all concepts from file files/output/concepts.json or files/output/aviation_concepts.json.
# List of ID-s of concepts is saved to files/output/
#requests_concepts.import_concepts('files/import/avi_1409/avi_concepts_with_word_ids.json')


######################
#  TEAR DOWN TEST DATA
######################
# Delete created sources
#requests_sources.delete_created_sources('files/output/ids_of_created_sources.json')
