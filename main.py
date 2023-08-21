import parse_concepts
import parse_sources


# Export sources from XML input/esterm.xml
file = parse_sources.export_sources_from_xml('files/input/esterm.xml')


# Get ID-s of existing sources. If source doesn't exist yet, create it and get its ID.
# Add the sources and their ID-s to file output/sources_with_ids.json

#with open('files/output/sources.json', 'r', encoding='utf-8') as file:
#    updated_sources = sources_import.sources_requests.check_sources_from_ekilex(file)

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