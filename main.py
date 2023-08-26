import parse_concepts
import parse_sources
import requests_concepts
import requests_sources

# First parse XML and find potential expert names. Then create sources for these experts
expert_sources = parse_sources.create_expert_sources(parse_sources.export_experts_names_from_xml('files/input/esterm.xml'))

# 1. Export sources from XML input/esterm.xml. Add expert sources to it as well. Returns sources files/output/sources.json
file = parse_sources.export_sources_from_xml('files/input/esterm.xml', expert_sources)

# 2. Get ID-s of existing sources. If source doesn't exist yet, create it and get its ID.
# Add the sources with their ID-s to file output/sources_with_ids.json
# Add ID-s of created sources to files/output/ids_of_created_sources.json

#updated_sources = requests_sources.assign_ids_to_all_sources('files/output/sources.json')

# 3. Export concepts from XML. Returns files/output/concepts.json and files/output/aviation_concepts.json
#parse_concepts.transform_esterm_to_json(updated_sources)

# 4. Import all concepts from file files/output/concepts.json or files/output/aviation_concepts.json.
# List of ID-s of concepts is saved to files/output/
#requests_concepts.import_concepts('files/output/concepts.json')


######################
## TEAR DOWN TEST DATA
######################
#requests_sources.delete_created_sources('files/output/ids_of_created_sources.json')