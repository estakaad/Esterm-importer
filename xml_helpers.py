# Find term"s or definition"s languages and match it with
# the language abbreviation used in API
def match_language(lang):
    if lang == "FR":
        lang_name = "fra"
    if lang == "EN-GB":
        lang_name = "eng"
    if lang == "ET":
        lang_name = "est"
    if lang == "FI":
        lang_name = "fin"
    if lang == "RU":
        lang_name = "rus"
    if lang == "XO":
        lang_name = "xho"
    # Actually no idea what language is XH
    if lang == "XH":
        lang_name = "xho"
    if lang == "DE":
        lang_name = "deu"
    return lang_name


# Return list of all unique languages present in XML
def find_all_languages(root):
    all_languages = []
    for term in root.findall(".//languageGrp"):
        for lang in term.findall(".//language"):
            all_languages.append(lang.attrib["lang"])

    set_res = set(all_languages)
    unique_languages = (list(set_res))

    return unique_languages


def find_all_description_types(root):
    all_description_types = []
    for term in root.findall(".//descripGrp"):
        for description_type in term.findall(".//descrip"):
            all_description_types.append(description_type.attrib["type"])

    set_res = set(all_description_types)
    unique_description_types = (list(set_res))

    return unique_description_types