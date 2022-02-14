import unittest
import pathlib
import logging
import shutil

from templer import Utils, ExtendedDict
from pathlib import WindowsPath
ROOT_PATH = pathlib.Path(__file__).parent.absolute()
PATH_TESTS = ROOT_PATH / 'tests'
PATH_RESULT = PATH_TESTS / 'result'
PATH_TEST_DIR = PATH_TESTS / 'test_path'
PATH_TEST_TMPL = PATH_TEST_DIR / 'test_file_tmpl'
TEST_POINTER = PATH_TESTS / 'test_pointer.yaml'


class TestUtils(unittest.TestCase):
    def setUp(self) -> None:
        self.utilities = Utils()
        self.utilities.logging.basicConfig(level=logging.CRITICAL)

    def test_load_yaml_file(self):
        actual = self.utilities.loadYaml(yaml_file=TEST_POINTER)
        self.assertIs(type(actual), dict)
        key = 'DEFAULT'
        expected = {'DEFAULT': {'segsize': 'walsegsize'}}
        self.assertDictContainsSubset(expected[key], actual[key])

    def test_load_yaml_not_exist(self):
        try:
            actual = self.utilities.loadYaml(
                yaml_file=PATH_TESTS / 'not_found.yaml')
            self.assertTrue(False, msg='Нет ошибки после выполения')
        except BaseException as e:
            self.assertEqual('1', str(e))

    def test_separate_names_with_comas(self):
        expected = ['ab', 'af', 'cfv', 'adg']
        actual = '  ab, af,  cfv ,  adg'
        actual = self.utilities.separateNamesWithCommas(actual)
        self.assertEqual(expected, actual[0])

    def test_reserved_variables_set(self):
        expected = r"Text{{SPACE}}{{CouNT}}{{EMPTY}}{{TAB}}{{NEWSTR}}{{VAR}}"
        actual = "Text 5\t\nTEST"
        custom_variables = ['CouNT=5', 'VAR=TEST']
        expected = self.utilities._reservedVariables(
            expected, custom_variables)
        self.assertEqual(expected, actual)

    def test_rewrite_reserved_variables_set(self):
        expected = r"Text{{SPACE}}{{CouNT}}{{EMPTY}}{{TAB}}{{NEWSTR}}{{VAR}}"
        custom_variables = ['SPACE=5', 'VAR=TEST']
        try:
            expected = self.utilities._reservedVariables(
                expected, custom_variables)
            self.assertTrue(False, msg='Нет ошибки после выполения')
        except BaseException as e:
            self.assertEqual('1', str(e))

    def test_get_variables_for_pointer(self):
        expected = {'VAR': 'TEST', 'JT': '5'}
        custom_variables = ['VAR=TEST', 'JT=5']
        actual = self.utilities.get_variables_for_pointer(custom_variables)
        self.assertEqual(expected, actual)

    def test_excludes_variables_for_pointer(self):
        custom_variables = ['SPACE=5', 'VAR=TEST', 'JT=5']
        try:
            self.utilities.get_variables_for_pointer(
                custom_variables, exclude_variables=['SPACE', 'EMPTY'])
            self.assertTrue(False, msg='Нет ошибки после выполения')
        except BaseException as e:
            self.assertEqual('1', str(e))

    def test_get_number_lines(self):
        vendor = 'ROSA73'
        expected = {vendor: [96, {'(*)': 97, 'os_name': 98, 'os_adder': 99, 'text_name': 100, 'docker_image': 101,
                                  'docker_command': 102, 'cmake_version': 103, 'python3_devel': 104, 'python_devel': 106}]}
        actual = self.utilities.get_number_lines(TEST_POINTER)
        self.assertEqual(expected[vendor], actual[vendor])


class TestClassExtendedDict(unittest.TestCase):
    def setUp(self) -> None:
        self.yaml_dict = Utils().loadYaml(TEST_POINTER)
        self.extendedDict = ExtendedDict(self.yaml_dict, TEST_POINTER)
        self.os_list = ['ALT8', 'REDOS73', 'ALT82', 'ALT91', 'ALTEROS7', 'CENTOS78', 'CENTOS82', 'opensuse15sp3',
                        'opensuse42sp3', 'oracle78', 'oracle84', 'redos72', 'redos73', 'rhel78', 'rhel79', 'rhel82', 'rosA73']
        shutil.rmtree(PATH_RESULT, True)

    def test_find_all_paths_to_directory(self):
        expected = {WindowsPath('test_path'): ['test_file_tmpl'], WindowsPath('.'): [
            'test_pointer.yaml', '__init__.py']}
        actual = self.extendedDict._find_all_paths(PATH_TESTS)
        self.assertEqual(expected, actual)

    def test_delete_unusing_templates(self):
        tmpl = open(PATH_TEST_TMPL, encoding='utf-8').readlines()
        file_name = PATH_TEST_TMPL.parts[-1]
        os = 'ALT8'
        not_expected = [r'{{find_debug}}', r'{{set_verify_method}}']
        actual = self.extendedDict._delete_unusing_templates(
            tmpl, os, file_name, PATH_TEST_DIR)
        for not_e in not_expected:
            self.assertNotIn(not_e, actual)

    def test_checking_inheritance(self):
        os_list = ['ALT8', 'REDOS73', 'ALT82', 'ALT91', 'ALTEROS7', 'CENTOS78', 'CENTOS82', 'opensuse15sp3',
                   'opensuse42sp3', 'oracle78', 'oracle84', 'redos72', 'redos73', 'rhel78', 'rhel79', 'rhel82', 'rosA73']
        os_list = [v.upper() for v in os_list]
        for oss in os_list:
            try:
                len_dict = len(self.extendedDict.dictionary[oss])
                RTN = self.extendedDict.checking_inheritance('ALT8')
                if len(self.extendedDict.dictionary[oss]) >= len_dict:
                    self.assertTrue(
                        True, 'Наследование для %s было использовано' % oss)
                else:
                    self.assertTrue(
                        False, 'Наследование для %s не было использовано' % oss)
            except:
                self.assertTrue(False, 'Проблемы с %s' % oss)

    def test_check_dublicate_values_between_one_level_collections(self):
        try:
            _ = self.extendedDict.check_dublicate_values_between()
        except Exception as e:
            self.assert_(False, e)

    def test_check_dublicate_values_to_one_collection(self):
        try:
            _ = self.extendedDict.check_dublicate_values_to_one_collection()
        except Exception as e:
            self.assert_(False, e)

    def test_check_availability_os(self):
        os_list = self.os_list
        os_list = [v.upper() for v in os_list]
        for oss in os_list:
            try:
                self.extendedDict.check_availability_os(oss)
            except Exception as e:
                self.assert_(False, e)

    def test_find_links_for_collection(self):
        os_list = self.os_list
        os_list = [v.upper() for v in os_list]
        for oss in os_list:
            try:
                self.extendedDict.finder_links(oss)
            except Exception as e:
                self.assert_(False, e)

    def test_update_dictionary_default_values(self):
        os_list = self.os_list
        os_list = [v.upper() for v in os_list]
        for oss in os_list:
            try:
                self.extendedDict.update_dict_default_values(oss)
            except Exception as e:
                self.assert_(False, e)

    def test_create_template_from_dict(self):
        os_list = self.os_list
        os_list = [v.upper() for v in os_list]
        for oss in os_list:
            try:
                self.extendedDict.create_from_template(
                    oss, PATH_TEST_DIR, PATH_RESULT)

            except Exception as e:
                self.assert_(False, e)


def suite():
    suite = unittest.TestSuite()
    suite.addTests(unittest.makeSuite(TestUtils))
    suite.addTests(unittest.makeSuite(TestClassExtendedDict))
    return suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())
