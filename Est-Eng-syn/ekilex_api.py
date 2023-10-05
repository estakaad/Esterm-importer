import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("API_KEY")

# Function to read json files
def read_json_path(directory, filename):
    with open(os.path.join(directory, f"{filename}.json"), 'r', encoding='utf-8') as f:
        return json.load(f)

# Function to write json files
def write_json_path(data, directory, filename, pretty_print=False):
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, f"{filename}.json"), 'w', encoding='utf-8') as f:
        if pretty_print:
            json.dump(data, f, indent=4)
        else:
            json.dump(data, f)

### TEST creds
api_url = 'https://ekitest.tripledev.ee/ekilex/api/'
resp_get = requests.get(url=api_url + 'endpoints',
                        headers={'ekilex-api-key': api_key})

#print(json.dumps(resp_get.json(), indent=2))


ekilex_data = read_json_path('output', 'cleaned_data')
missing_words = []
bad_requests = []
cnt = 1

for word_eq in ekilex_data:
    #print(word_eq)
    resp = requests.post(
        url=api_url + 'syn_candidate/create',
        headers={
            'ekilex-api-key': api_key,
            'Content-type': 'application/json',
            'Accept': 'application/json'
        },
        data=json.dumps(word_eq),
        params={'crudRoleDataset': 'eptest'}
    )
    print(resp.status_code)
    print(resp.content)
    print(cnt)
    cnt += 1
    if resp.status_code > 400:
        bad_requests.append((str(resp.content), word_eq))
    if resp.status_code == 200 and b'{"success":false,"message":"Headword does not exist"}' in resp.content:
        missing_words.append(word_eq)
    if cnt == 100:
        break

    write_json_path(bad_requests, 'logs', 'ekilex_import_bad_requests_import', pretty_print=True)
    write_json_path(missing_words, 'logs', 'ekilex_import_missing_words_import', pretty_print=True)

