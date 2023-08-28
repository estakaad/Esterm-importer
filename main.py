import parse_concepts
import parse_sources
import requests_concepts
import requests_sources
import json
import log_config


# logger = log_config.get_logger()

esterm_filename = 'files/input/esterm.xml'

# First parse XML and find potential expert names. Then create sources for these experts
# 13 sec
# expert_sources = parse_sources.create_expert_sources(esterm_filename)

# 1. Export sources from XML input/esterm.xml. Add expert sources to it as well.
# Returns sources files/output/sources.json
# sources_output_json_filename = 'files/output/sources.json'
#     file = parse_sources.export_sources_from_xml(esterm_filename, expert_sources)

# 2. Get ID-s of existing sources. If source doesn't exist yet, create it and get its ID.
# Add the sources with their ID-s to file output/sources_with_ids.json
# Add ID-s of created sources to files/output/ids_of_created_sources.json
# Return file output/sources_with_ids.json

#updated_sources_file = requests_sources.assign_ids_to_all_sources(sources_output_json_filename)


# 4,6 sekundit
# 3. Export concepts from XML. Returns files/output/concepts.json and files/output/aviation_concepts.json
with open('files/output/sources_with_ids.json', 'r', encoding='utf-8') as f:
    updated_sources = json.load(f)

parse_concepts.transform_esterm_to_json(updated_sources)

# 4. Import all concepts from file files/output/concepts.json or files/output/aviation_concepts.json.
# List of ID-s of concepts is saved to files/output/
#requests_concepts.import_concepts('files/output/concepts.json')


######################
#  TEAR DOWN TEST DATA
######################
# requests_sources.delete_created_sources('files/output/ids_of_created_sources.json')
