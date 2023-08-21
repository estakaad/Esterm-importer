import parse_concepts
import parse_sources
import requests_sources

# Export sources from XML input/esterm.xml. Returns sources files/output/sources.json
#file = parse_sources.export_sources_from_xml('files/input/esterm.xml')


# Get ID-s of existing sources. If source doesn't exist yet, create it and get its ID.
# Add the sources and their ID-s to file output/sources_with_ids.json

requests_sources.assign_ids_to_all_sources('files/output/sources.json', 'files/output/sources_with_ids.json')

# Export concepts from XML
#concepts = parse_concepts.transform_esterm_to_json()


# Import all other concepts to Ekilex


#
# # Save the concepts in output.json to Ekilex
# #
# json_output = 'output\\concepts.json'
#
# load_dotenv()
# api_key = os.environ.get("API_KEY")
# parameters = {}
# crud_role_dataset = os.environ.get("ESTERM")
#
# header = {"ekilex-api-key": api_key}
# parameters = {"crudRoleDataset": crud_role_dataset}
#
# concepts_import.concepts_requests.save_term(json_output, header, parameters, max_objects=1000)