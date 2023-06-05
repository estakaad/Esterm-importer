import api_requests
import os
from dotenv import load_dotenv
import parse_esterm


# Transform the external term base to JSON
# Transform Esterm
parse_esterm.transform_esterm_to_json()

# Save the concepts in output.json to Ekilex

#json_output = 'output\output.json'

load_dotenv()
api_key = os.environ.get("API_KEY")
parameters = {}
crud_role_dataset = os.environ.get("KALANDUS")

header = {"ekilex-api-key": api_key}
parameters = {"crudRoleDataset": crud_role_dataset}

#api_requests.save_term(json_output, header, parameters)