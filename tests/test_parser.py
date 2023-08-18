import unittest
from xml.etree import ElementTree as ET
from concepts_import import xml_helpers


class TestXmlHelpers(unittest.TestCase):

    def test_match_language(self):
        self.assertEqual(xml_helpers.match_language('FR'), 'fra')
        self.assertEqual(xml_helpers.match_language('EN-GB'), 'eng')
        self.assertEqual(xml_helpers.match_language('ET'), 'est')

    def test_match_language_unmatched(self):
        self.assertEqual(xml_helpers.match_language('x'), 'est')

    def test_match_language_empty(self):
        self.assertEqual(xml_helpers.match_language(None), 'est')

    def test_is_concept_aviation_related(self):
        test_cases = [
            ('tests/test_data/aviation_concept_ltb.xml', True),
            ('tests/test_data/aviation_concept_alamvaldkond_lennuvaljad.xml', True),
            ('tests/test_data/non_aviation_concept.xml', False),
        ]
        for xml_file, expected_result in test_cases:
            with self.subTest(xml_file=xml_file):
                with open(f'{xml_file}', 'rb') as file:
                    xml_content = file.read()

                    parser = ET.XMLParser(encoding='UTF-16')
                    root = ET.fromstring(xml_content, parser=parser)

                    concept_element = root.find('./conceptGrp')
                    self.assertEqual(xml_helpers.is_concept_aviation_related(concept_element), expected_result)


if __name__ == '__main__':
    unittest.main()