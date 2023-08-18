import json

# Load the sources_api.json file
with open('../sources_import/sources_api.json', 'r', encoding='utf-8') as file:
    sources_data = json.load(file)

# Create a list of all source names from sources_api.json
source_names = []
for source in sources_data:
    for prop in source['sourceProperties']:
        if prop['type'] == 'SOURCE_NAME':
            source_names.append(prop['valueText'])

# Load the other JSON file
with open('../files/output/concepts.json', 'r', encoding='utf-8') as file:
    concepts_data = json.load(file)

# Function to check if the source is present and update the object
def check_source(source_links):
    for source_link in source_links:
        value = source_link['value']
        if '§' in value:
            value = value.split('§')[0].strip()
        if value in source_names:
            source_link['isPresent'] = True
        else:
            source_link['isPresent'] = False

# Check and update sourceLinks in each concept
for data in concepts_data:
    if 'definitions' in data:
        for concept in data['definitions']:
            if 'sourceLinks' in concept:
                check_source(concept['sourceLinks'])
    if 'notes' in data:
        for note in data['notes']:
            if 'sourceLinks' in note:
                check_source(note['sourceLinks'])
    if 'words' in data:
        for word in data['words']:
            if 'lexemeSourceLinks' in word:
                check_source(word['lexemeSourceLinks'])
            for usage in word.get('usages', []):
                if 'sourceLinks' in usage:
                    check_source(usage['sourceLinks'])
            for note in word.get('lexemeNotes', []):
                if 'sourceLinks' in note:
                    check_source(note['sourceLinks'])

# Save the modified JSON as concepts_with_sources.json
with open('../concepts_with_sources.json', 'w', encoding='utf-8') as file:
    json.dump(concepts_data, file, indent=4, ensure_ascii=False)
