import concepts_import.parse_esterm
import sources_import.sources
import os
from dotenv import load_dotenv
from sources_import import sources_requests
from concepts_import import parse_esterm

# Export sources from XML
#file = sources_import.sources.export_sources_from_xml('files/input/esterm.xml')

# Check if sources exist in Ekilex. If they don't, create them. In either case, add their ID-s to file sources_with_ids.json
#
#with open('files/output/sources.json', 'r', encoding='utf-8') as file:
#    updated_sources = sources_import.sources_requests.check_sources_from_ekilex(file)

# Export concepts from XML
concepts = concepts_import.parse_esterm.transform_esterm_to_json()


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