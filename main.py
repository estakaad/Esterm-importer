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

# # 1. Compile JSON with expert sources. Contains
# # - EKSPERT, PÄRING, CONSILIUM, DELEST, DGT, PARLAMENT type sources from esterm.xml
# # - metadata from eksperdid.xlsx
# # # # # # # # # #
# input_excel = 'files/input/ekspertide_lisainfo.xlsx'
# output_json = 'files/output/sources/eksperdid.json'
# expert_info_from_esterm = 'files/input/eksperdid_estermist.csv'
# expert_info_for_api_calls = 'files/import/2024-11-04_SOURCES/expert_sources.json'
#
# expert_sources_helpers.excel_to_json(input_excel, output_json)
# expert_sources_helpers.create_experts_sources(output_json, expert_info_from_esterm, expert_info_for_api_calls)

# 2. Export sources from XML input/esterm.xml.
# # # # Returns sources files/output/sources/sources.json
# sources_without_ids_filename = 'files/output/sources/sources.json'
# file = parse_sources.export_sources_from_xml(esterm_filename, sources_without_ids_filename)

# 3. Get ID-s of existing sources. If source doesn't exist yet, create it and get its ID.
# Add the sources with their ID-s to file output/sources/sources_with_ids.json
# Add ID-s of created sources to files/output/sources/ids_of_created_sources.json
# Return file output/sources/sources_with_ids.json
# # # #
# sources_without_ids_filename = 'files/import/2024-11-04_SOURCES/unknown_sources.json'
# sources_with_ids_filename = 'files/import/2024-11-04_SOURCES/unknown_sources_with_ids-04112023.json'
# sources_added_ids_filename = 'files/import/2024-11-04_SOURCES/ids_of_created_unknown_sources-04112023.json'
# updated_sources_file = requests_sources.assign_ids_to_all_sources(
#     sources_without_ids_filename, sources_with_ids_filename, sources_added_ids_filename)

# # 4. Add expert sources. No need to check if it exists, because we know they don't.
# # # Add IDs to files/output/sources/expert_sources.json
# expert_sources_without_ids_filename = 'files/output/sources/terminoloogid.json'
# expert_sources_with_ids_filename = 'files/output/sources/terminoloogid_with_ids.json'
# ids_of_created_expert_sources_file = 'files/output/sources/terminoloogid_ids.json'
# updated_expert_sources_file = requests_sources.assign_ids_to_expert_sources(
#      expert_sources_without_ids_filename, expert_sources_with_ids_filename, ids_of_created_expert_sources_file)
# #
# # # # # 5. Map source names to their ID-s
with open('files/import/2024-11-04_SOURCES/sources_with_ids_and_unknown_sources_with_ids-04112023.json', 'r', encoding='utf-8') as f:
    updated_sources = json.load(f)

name_to_id_map = xml_helpers.create_name_to_id_mapping(updated_sources)

with open('files/import/2024-11-04_SOURCES/expert_sources_with_ids.json', 'r', encoding='utf-8') as f:
    expert_sources = json.load(f)

expert_names_to_ids_map = expert_sources_helpers.create_name_and_type_to_id_mapping_for_expert_sources(expert_sources)

with open('files/output/sources/terminoloogid_with_ids.json', 'r', encoding='utf-8') as f:
    term_sources = json.load(f)

term_sources_to_ids_map = expert_sources_helpers.create_terminologist_name_value_to_id_mapping(term_sources)
#
# # # # 6. Export concepts from XML. Returns files/output/concepts.json and files/output/aviation_concepts.json
parse_concepts.transform_esterm_to_json(name_to_id_map, expert_names_to_ids_map, term_sources_to_ids_map)

# 7. Check if word exists. If it does, add its ID
#requests_concepts.update_word_ids('files/output/aviation_concepts.json', 'eki', 'avi2110')
#requests_concepts.update_word_ids('files/output/concepts.json', 'eki', 'est2110')


# 8. Import all concepts from file files/output/concepts.json or files/output/aviation_concepts.json.
# List of ID-s of concepts is saved to files/output/
# NB! Update folder where saved and not saved concepts are saved
#requests_concepts.import_concepts('files/import/avi2110/avi2110_concepts_with_word_ids.json', 'avi')
#requests_concepts.import_concepts('files/import/est2110/est2110_concepts_with_word_ids.json', 'est')


######################
#  TEAR DOWN TEST DATA
######################
# Delete created sources

#sources_added_ids_filename = 'files/import/2023-10-27_SOURCES/ids_of_created_expert_sources.json'
#sources_added_ids_filename = 'files/import/2023-10-27_SOURCES/ids_of_created_unknown_sources-test-271023.json'
#sources_added_ids_filename = 'files/import/2023-10-27_SOURCES/uus.json'
#requests_sources.delete_created_sources(sources_added_ids_filename)