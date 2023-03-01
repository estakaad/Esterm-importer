import requests

api_key='6a8c350b1b8d4d4ab753849033bce585'
base_url='https://ekitest.tripledev.ee/ekilex/api/'
post_word='https://ekitest.tripledev.ee/ekilex/api/term-meaning/save?crudRoleDataset=mlt'
crudRoleDataset='mlt'
word_id=2329062

json_object={
    "datasetCode": "mlt",
    "definitions": [
        {
            "value": "definition #3",
            "lang": "eng",
            "definitionTypeCode": "definitsioon"
        },
        {
            "value": "definitsioon #4",
            "lang": "est",
            "definitionTypeCode": "definitsioon"
        },
    ],
    "words": [
        {
            "value": "word432",
            "lang": "eng"
        },
        {
            "value": "keelend321",
            "lang": "est"
        },
    ]
}


headers = {'ekilex-api-key': api_key}

#res = requests.get(base_url + '/term-meaning/details/2329062?crudRoleDataset=mlt', headers=headers)

res = requests.post('https://ekitest.tripledev.ee/ekilex/api/term-meaning/save?crudRoleDataset=mlt',json=json_object,headers=headers)

#res = requests.get(base_url+'datasets', headers=headers)

print(res)
