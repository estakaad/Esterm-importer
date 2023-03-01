import requests
from dotenv.main import load_dotenv
import os


load_dotenv()
api_key=os.environ.get('API_KEY')


json_object={
    "datasetCode": "mlt",
    "definitions": [
        {
            "value": "eelarve aasta kohta [<xref Tlink=\"Allikas:EKSS\">EKSS</xref>]_test",
            "lang": "est",
            "definitionTypeCode": "definitsioon"
        }
    ],
    "words": [
        {
            "value": "annual budget_test",
            "lang": "eng"
        },
        {
            "value": "aastaeelarve_test",
            "lang": "est"
        },
        {
            "value": "budget annuel_test",
            "lang": "fra"
        },

    ]
}


headers = {'ekilex-api-key': api_key}
res = requests.post('https://ekitest.tripledev.ee/ekilex/api/term-meaning/save?crudRoleDataset=mlt',json=json_object,headers=headers)

print(res)
