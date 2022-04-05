# -*- coding: utf-8 -*-

import sys
import pathlib
import re
import argparse
import logging
import yaml as depYaml

sys.path.append('libs')
from os import walk
from os.path import realpath
from typing import Set, Tuple, List
from libs.ruamel import yaml

TEMPLER_PROG_NAME = 'templer'
TEMPLER_VERSION = '1.1.0'

class Utils:
    """
    Утилита для обработки, преобразований различных данных в другие
    """

    def __init__(self) -> None:
        """Заглушка на будущее)
        """
        self.logging = logging

    def separateNamesWithCommas(self, names: str) -> Tuple[dict, str]:
        """Функция для разделения строки, в которой есть запятые, на элементы в массиве и
        исключения возможность появления у строк массива лишних пробелов в начале и конце

        Args:
            names (str): Строка, которая будет разделена по запятым

        Returns:
            Tuple[dict,str]: Массив строк и оригинальная строка
        """
        raw_name = names
        names = names.split(',')
        for index, nm in enumerate(names):
            if nm.startswith(' '):
                nm = nm.lstrip()
            if nm.endswith(' '):
                nm = nm.rstrip()
            names[index] = nm
        return names, raw_name

    def loadYaml(self, yaml_file: pathlib.Path) -> dict:
        """ Загрузка YAML-файла, его валидация и преобразование в словарь

        Args:
            yaml_file (pathlib.Path): Путь до YAML-файла

        Raises:
            sys.exit: Вызов исключения происходит, если YAML-файл был интерпретирован неверно, и вывод соотвествующей ошибки

        Returns:
            dict: Преобразованный YAML-файл в словарь для дальнейшней машино-читаемой обработки
        """
        try:
            with open(yaml_file, 'r', encoding='utf-8') as rd:
                pointer = yaml.safe_load(rd)
        except FileNotFoundError as e:
            logging.error("Файла-указателя %s не существует " % yaml_file)
            raise sys.exit(1)
        except Exception as e:
            logging.error(e)
            raise sys.exit(1)

        return pointer

    def _reservedVariables(self, stringer: str, options_argv) -> str:
        """Использование предопределенных переменных, которые используются в значениях параметров
        например, {{SPACE}} - замещается в пробелом. 
        Это необходимо если при преобразовании из YAML в словарь были срезаны пробелы, отступы и новые пустые строки, а
        нужно 1:1 проверить сгенерированные сборочные файлы к оригинальным

        Args:
            stringer (str): Строка, в которой есть преопределенные переменные, например, {{SPACE}}

        Returns:
            str: Возвращает строку, с замещенными переменными на их значения
        """
        variables = {'SPACE': ' ', 'EMPTY': '', 'TAB': '\t', 'NEWSTR': '\n'}
        add_var = self.get_variables_for_pointer(
            options_argv, exclude_variables=variables.keys())
        variables.update(add_var)
        pattern_insert = r'{{%s}}'
        value = stringer
        # print(stringer)
        reg_finder = re.findall(r'\{\{([A-z,_,0-9]+)\}\}', value)
        find_unused_var = set(reg_finder).difference(set(variables.keys()))
        if find_unused_var:
            find_unused_var = [pattern_insert % v for v in find_unused_var]
            logging.error(
                'Указанны переменные %s в файле-указателе, но не используются. Необходимо убрать переменные, либо указать их при помощи -v/--variable' % ",".join(find_unused_var))
            sys.exit(1)
        if type(value) is str:
            for vars in variables:
                value: str = value.replace(
                    pattern_insert % vars, variables[vars])

        return value

    def get_variables_for_pointer(self, arguments, exclude_variables: list = []):
        # parse variables
        variables = {}
        arguments = [] if not arguments else arguments
        for argu in arguments:
            if type(argu) is str:
                vari = argu.split('=')
                if len(vari) != 2:
                    logging.error(
                        'Формат указания переменной %s не соотвествует формату -v/--variable VARIABLE=VALUE' % "".join(vari))
                    sys.exit(1)
                elif len(vari) == 2:
                    variable = vari[0].strip()
                    if variable in exclude_variables:
                        logging.error('Нельзя перезаписать переменную %s из списка зарервированных %s' % (
                            variable, ",".join(exclude_variables)))
                        sys.exit(1)
                    value = vari[1].strip()
                    variables[variable] = value

            else:
                logging.error(
                    'Значение для консольного аргумента (-v/--variable) должно иметь строковый тип')
                sys.exit(1)
        return variables

    def get_number_lines(self, yaml_file: pathlib.Path):
        """Получить номер для строк, в которых название классов и их атрибутов

        Args:
            yaml_file (pathlib.Path): Путь до файла-указателя

        Returns:
            dict: Словарь, с номерами строк для классов и их атрибутов
        """
        file = open(yaml_file, 'r', encoding='utf-8').readlines()
        find_class = False
        find_attr = False
        first_start = 0
        second_start = 0
        regex_compile = re.compile(r'[^:,\s]*[\s]*[:]')
        current_class = None
        dict_lines: dict = {}
        for number_line, line in enumerate(file):
            number_line += 1
            class_ = re.search(regex_compile, line)
            if class_:
                indc = class_.regs[0][0]
                if indc <= first_start:
                    find_class = False
                if not find_class:
                    first_start = indc
                    find_class = True
                    current_class = class_.string[class_.regs[0]
                                                  [0]:class_.regs[0][1]-1]
                    dict_lines[current_class] = [number_line, {}]
                    continue
                else:
                    indc = class_.regs[0][0]
                    if not find_attr:
                        find_attr = True
                        second_start = class_.regs[0][0]

                    if indc > first_start and indc <= second_start:
                        attr = class_.string[class_.regs[0]
                                             [0]:class_.regs[0][1]-1]
                        attr = attr.strip()
                        dict_lines[current_class][1].update(
                            {attr: number_line})

        return dict_lines


class ExtendedDict(dict):
    """Расширенный класс <dict>, в который входят дополнительные возможности работы над словарем: 
    находить по вложенностям ссылочные указатели (название ключей первого уровня) и объединять содержимое, что
    похоже на классическое наследование классов и др.

    Args:
        dict ([dict]): Преобразованный и готовый к работе словарь
    """

    def __getitem__(self, __k: object) -> object:
        return self.dictionary.__getitem__(__k)
        
    def __init__(self, dictionary: dict, yaml_file_path: str):
        """Иницилизация класса, с указанием глобальных переменных и композитных классов (Utils, logging)

        Args:
            dictionary (dict): Преобразованный словарь из YAML-файла
            yaml_file_path (str): Путь до YAML-файла
        """
        super().__init__(dictionary)
        self.dictionary = dictionary
        self.utilities = Utils()
        self.encoding = 'utf-8'
        self.yaml_file_path = yaml_file_path
        self.nameClassParam = '(*)'
        self.nameArrowLink = '->'
        self.path_script = pathlib.Path(realpath(__file__))
        self.logging = logging
        self.pattern_regex = r'\{\{[A-z,0-9,_]{1,}\}\}'

        # pre function
        self.dictionaryLines = self.utilities.get_number_lines(yaml_file_path)
        self.allDictParams = self.__get_all_using_params()

    def __get_all_using_params(self):
        """Получить из еще непреобразованного словаря, сформированному из YAML, все параметры 2-ого уровня
        для получения актульного списка ключевых слов, которые используются в шаблонах (даже если для определенной 
        операционной системы в данный момент не используется, но в рамках файла-указателя, используется)

        Returns:
            set: Все параметры из словаря
        """
        all_params: set = set()
        for os_name in self.dictionary.keys():
            for param in self.dictionary[os_name]:
                if param not in [self.nameClassParam]:
                    all_params.add("{{%s}}" % param)
        return all_params

    def _find_all_paths(self, path_tmpl: pathlib.Path) -> dict:
        """Поиск всех подпапок в директории шаблонов

        Args:
            path_tmpl (pathlib.Path): Путь до основной директории с шаблонами

        Raises:
            sys.exit: Возврат ошибки, если директории с подготовленными шаблонами не существует

        Returns:
            dict: Возвращает все поддиректории
        """
        path_to_templation = {}
        for root, dirs, files in walk(path_tmpl, topdown=False):
            current_path = pathlib.Path(root).relative_to(path_tmpl)
            for name in files:
                if not path_to_templation.get(current_path):
                    path_to_templation[current_path] = []
                path_to_templation[current_path].append(name)

        if not path_to_templation:
            logging.error(
                'Директории <%s> с подготовленными шаблонами не существует!' % path_tmpl)
            raise sys.exit(1)

        return path_to_templation

    def _delete_unusing_templates(self, tmpl: list, os_name: str, file_name: str, tmpl_path: pathlib.Path) -> str:
        """Для отключения устаревших или неиспользуемых шаблонированных переменных

        Args:
            tmpl (list): Файл-шаблона, разбитый построчно в список
            os_name (str): Название операционной системы
            file_name (str): Имя файла-шаблона
            tmpl_path (pathlib.Path): Путь до директории с шаблонами

        Returns:
            str: Возвращает готовый по шаблону файл
        """
        tmpl = "".join(tmpl)
        
        find_unused_templates = re.findall(self.pattern_regex, tmpl)
        deprecated_params = set(
            find_unused_templates).difference(self.allDictParams)
        find_unused_templates = ",".join(find_unused_templates)
        deprecated_params = ",".join(deprecated_params)

        path_to_tmpl_file = str(tmpl_path / file_name)

        if deprecated_params:
            logging.warning('УСТАРЕЛИ переменные-шаблоны <%s> указанные в файле. Можно их удалить!\n\tФайл: "%s"' %
                            (deprecated_params, path_to_tmpl_file))
        if find_unused_templates:
            logging.info('Переменные-шаблоны <%s> не используются в файле <%s> для <%s> и будут удалены в процессе создания шаблона'
                         % (find_unused_templates, file_name, os_name))
        # зачистка одиночных переменных в строке (с оступами и без)
        tmpl = re.sub(r"[ ,\t,]+%s\n" % self.pattern_regex, '', tmpl)
        tmpl = re.sub(r"\n%s\n" % self.pattern_regex, '\n', tmpl)
        # Для удаления inline-переменных
        tmpl = re.sub(r"%s" % self.pattern_regex, '', tmpl)
        return tmpl

    def __construct_traceback(self, preclass: str, inherit_class: str, param: str):
        """Для построяния ссылок на строки с ошибками

        Args:
            preclass (str): Самый нижний, дочерний класс
            inherit_class (str): Наследуемый класс
            param (str): Возможно-переопределяемый параметр другим классом
        """
        numbers = [
            self.dictionaryLines[preclass][1].get(self.nameClassParam),
            self.dictionaryLines[inherit_class][1].get(param),
            self.dictionaryLines[preclass][1].get(param)
        ]
        num_st = '\n\tСтрока, где наследуется класс в файле-указателе: "%s", line %s' % (
            self.yaml_file_path, numbers[0]) if numbers[0] else ''
        num_st2 = '\n\tCтрока, где параметр наследуемого класса: "%s", line %s' % (
            self.yaml_file_path, numbers[1]) if numbers[1] else ''
        num_st3 = '\n\tCтрока, где параметр переопределяется: "%s", line %s' % (
            self.yaml_file_path, numbers[2]) if numbers[2] else ''

        logging.warning('Дочерний класс <%s> переопределяет атрибут <%s> наследуемого класса <%s>' % (
            preclass, param, inherit_class) + num_st + num_st3 + num_st2 + '\n')

    def __add_to_links_os_name(self, dictionary, os_name):
        """Для добавления в словарь, где указаны ссылки на атрибуты классов (link: CLASS)
        имени класса, который добавляет значение по ссылке к себе в словарь
        Нужно для понимания другими функциями контекста

        Args:
            dictionary ([type]): Преобразованный словарь из YAML-файла
            os_name ([type]): Название операционной системы

        Returns:
            [dict]: Изменный словарь, с добавленными комментариями для ссылок
        """
        for keys, items in dictionary.items():
            # проверка типа значения к параметру - чтобы различать обычный текст, и добавленные функции
            if type(items) is dict:
                if items.get(self.nameArrowLink):
                    # os_linker = items[self.nameArrowLink]
                    dictionary[keys].update({'__name_os': os_name})
                else:
                    continue

        return dictionary
        ...

    def checking_inheritance(self, os_name: str) -> None:
        """Поиск и применение наследование для указанной операционной системы в указателе

        Args:
            os_name (str): Название операционной системы

        Raises:
            sys.exit: Возврат ошибки
        """
        dictionary = self.dictionary
        key_for_inherit_classes = self.nameClassParam
        preclass = os_name
        current_used_classes = [os_name]

        def __recurse():
            nonlocal preclass
            os_dict = dictionary[os_name]
            if key_for_inherit_classes in os_dict:
                classes = os_dict[key_for_inherit_classes]
                if type(classes) is not list:
                    classes = [str(classes)]
                repeat_classes_inheritance = set(
                    current_used_classes) & set(classes)
                if not repeat_classes_inheritance:
                    current_used_classes.extend(classes)
                else:
                    for rpt in repeat_classes_inheritance:
                        wh_c = '\n\tСтрока, где наследуется класс в файле-указателе: "%s", line %s' % (
                            self.yaml_file_path, self.dictionaryLines[preclass][0])
                        wh_c2 = '\n\tСтрока, где наследуется класс в файле-указателе: "%s", line %s' % (
                            self.yaml_file_path, self.dictionaryLines[rpt][0])
                        logging.error('Класс <%s> не может быть унаследован <%s> так, как он уже сам использует родителя <%s>' % (
                            rpt, preclass, preclass)+wh_c+wh_c2)

                    sys.exit(1)

                for class_ in classes:
                    if class_ not in dictionary.keys():
                        logging.error(
                            'Наследуемый класс <%s> не существует и его не определить для <%s>\n\tCтрока "%s", line %s' % (class_, os_name, self.yaml_file_path, self.dictionaryLines[os_name][1][self.nameClassParam]))
                        raise sys.exit(1)

                    # атрибуты наследуемого класса
                    tmp_dict = dictionary[class_]
                    tmp_dict = self.__add_to_links_os_name(tmp_dict, class_)
                    for params in tmp_dict:
                        if params not in os_dict.keys():
                            dictionary[os_name][params] = tmp_dict[params]
                        else:
                            self.__construct_traceback(
                                preclass, class_, params)
                if key_for_inherit_classes in tmp_dict:
                    preclass = class_
                    dictionary[os_name][key_for_inherit_classes] = tmp_dict[key_for_inherit_classes]
                    __recurse()
                else:
                    del dictionary[os_name][key_for_inherit_classes]
                    # Возврат словаря не требуется так, как он изменяется через глобальный атрибут класса
                    return
        __recurse()

    def check_dublicate_values_between(self):
        """Проверка на наличие дублирующих значений одинаковых аргументов у разных коллекций
        """
        all_key_one_level = self.dictionary.keys()
        for_compare = []
        checked = []
        for key_level in all_key_one_level:
            checked.append(key_level)
            for key_level_1 in all_key_one_level:
                if key_level_1 not in checked:
                    for_compare.append((key_level, key_level_1))
        for key_1, key_2 in for_compare:
            common_arguments = set(self.dictionary[key_1]) & set(
                self.dictionary[key_2])
            for argu in common_arguments:
                left_value = self.dictionary[key_1][argu]
                right_value = self.dictionary[key_2][argu]
                if type(left_value) == type(right_value):
                    if type(left_value) is str:
                        right_value = right_value.strip()
                        left_value = left_value.strip()
                    if left_value == right_value:
                        logging.info('Коллекции <%s> и <%s> имеют одинаковые значения для одних тех же аргументов (параметров) - можно упростить!' % (key_1, key_2) +
                                     '\n\tВ коллекции <%s> параметр <%s>: "%s", line %s' % (key_1, argu, self.yaml_file_path, self.dictionaryLines[key_1][1][argu]) +
                                     '\n\tВ коллекции <%s> параметр <%s>: "%s", line %s' % (
                            key_2, argu, self.yaml_file_path, self.dictionaryLines[key_2][1][argu])
                        )

    def check_dublicate_values_to_one_collection(self):
        """Проверка на наличие дублирующих значений аргрументов в пределах одной коллекции,
        но проверка по всем имеющимся операционным системам
        """
        all_key_one_level = self.dictionary.keys()

        for key_level in all_key_one_level:
            for_compare = []
            checked = []
            dict_level = self.dictionary[key_level]
            for key_two_level in dict_level.keys():
                checked.append(key_two_level)
                for key_two_level_2 in dict_level.keys():
                    if key_two_level_2 not in checked:
                        for_compare.append((key_two_level, key_two_level_2))

            for key_1, key_2 in for_compare:
                if type(dict_level[key_1]) is str and type(dict_level[key_2]) is str:
                    left_string: str = dict_level[key_1].strip()
                    right_string: str = dict_level[key_2].strip()
                    if left_string == right_string:
                        logging.warning('Значение аргументов <%s> и <%s> повторяются в пределах коллекции %s' % (key_1, key_2, key_level) +
                                        '\n\tПри аргументе <%s>: "%s", line %s' % (key_1, self.yaml_file_path, self.dictionaryLines[key_level][1][key_1]) +
                                        '\n\tПри аргументе <%s>: "%s", line %s' % (
                                            key_2, self.yaml_file_path, self.dictionaryLines[key_level][1][key_2])
                                        )

    def check_availability_os(self, os_name: str):
        """Проверка доступности операционной системы в нашей системе шаблонов

        Args:
            os_name (str): Название операционной системы

        Raises:
            sys.exit: Вызывается ошибка завершения программы, если нет ОС в шаблоне
        """
        defines = self.dictionary.keys()

        if not os_name in self.dictionary.keys():
            matched_keys = ["<%s>" % cf.lower()
                            for cf in defines if os_name in cf]

            if matched_keys:
                logging.error('Возможно вы имели ввиду ' +
                              " или ".join(matched_keys))
            if not matched_keys:
                logging.error(
                    'Нет операционной системы <%s> в указателе!' % os_name)
            raise sys.exit(1)

    def finder_links(self, os_name) -> None:
        """Если в значение к параметру присвоен стрелочный указатель на существующий класс,
        то благодаря этой функции, стрелочный указатель будет заменён значением существующего параметра из
        указанного класса в YAML

        Args:
            os_name (dict): Аббревиатура, название операционной системы
        """
        os_dict = self.dictionary
        define_name_class = os_name
        for keys, items in os_dict[os_name].items():
            # проверка типа значения к параметру - чтобы различать обычный текст, и добавленные функции
            if type(items) is dict:
                if items.get(self.nameArrowLink):
                    os_linker = items[self.nameArrowLink]
                    define_name_class = items.get('__name_os', os_name)
                else:
                    continue
                # проверить объект ссылки существует
                have_link = os_dict.get(os_linker)
                if have_link and have_link.get(keys):
                    os_dict[os_name][keys] = have_link[keys]

                elif not have_link:
                    logging.error('<%s> не существует для создания ссылки на параметр <%s> в коллеции <%s>\n\tCтрока "%s", line %s' % (
                        os_linker, keys, define_name_class, self.yaml_file_path, self.dictionaryLines[define_name_class][1][keys]))
                    sys.exit(1)

                else:
                    logging.error('Неверно указана ссылка <%s> для <%s> на <%s>\n\tCтрока "%s", line %s' % (
                        keys, define_name_class, os_linker, self.yaml_file_path, self.dictionaryLines[define_name_class][1][keys]))
                    sys.exit(1)

    def update_dict_default_values(self, os_name: str):
        """
        Обновление выбранного словаря (по операционной системе) дефолтными значениями для параметров,
        которые не были ни унаследованы, ни задекларированы

        Args:
            os_name (str): Аббревиатура, название операционной системы
        """
        os_dict: dict = self.dictionary
        exist_params = os_dict[os_name].keys()
        if os_dict.get('DEFAULT'):
            default_dict = os_dict['DEFAULT']

            # значения параметров, которые не указаны
            not_exist_params = [
                ks for ks in default_dict if ks not in exist_params]

            for nep in not_exist_params:
                os_dict[os_name][nep] = default_dict[nep]

    def create_from_template(self, osname:str, path_to_tmpls: pathlib.Path, path_to_results: pathlib.Path, exclude_files: List[pathlib.Path] = [],variable_set:str=None):
        """Создание результирующих файлов по шаблонам, а при помощи обработанного и преобразованного
        словаря-указателя будет происходить замена шаблонированных переменных на значения из указателя (YAML-файла)

        Args:
            path_to_tmpls (pathlib.Path): Путь, где хранятся все шаблоны
            path_to_results (pathlib.Path): Путь, куда сохранять результирующие файлы
            exclude_files (List[pathlib.Path]): Исключенные из шаблонирования файлы
        """
        os_dict = self.dictionary
        listPathWhereTemplates = self._find_all_paths(path_to_tmpls)
        exclude_files = [v.parts[-1] for v in exclude_files]
        exclude_files.append(self.path_script.parts[-1])
        exclude_files.append('requirements.txt')
        if path_to_results.parts[-1] in exclude_files:
            logging.error(
                'Нельзя записать результаты шаблонов в файл: %s' % path_to_results)
            raise sys.exit(1)
        if path_to_results == path_to_tmpls:
            logging.error('Пути чтения шаблонов и записи результатов должны быть разными\n\t"%s" != "%s"' % (
                path_to_tmpls, path_to_results))
            raise sys.exit(1)
        print('Создание файлов по шаблону в директорию: %s' % path_to_results)
        for directories, file_names in listPathWhereTemplates.items():

            # директории шаблонов и результирующих файлов
            directory_tmpl: pathlib.Path = path_to_tmpls / directories
            directory_result: pathlib.Path = path_to_results / directories
            directory_result.mkdir(
                parents=True) if not directory_result.exists() else None

            for file_name in file_names:
                if file_name in exclude_files:
                    continue
                tmpl: list = open(directory_tmpl / file_name,
                                  'r', encoding=self.encoding).readlines()

                dict_via_os = os_dict[osname]
                for params in dict_via_os:
                    stringer = dict_via_os[params]

                    if type(stringer) is not str:
                        stringer = str(stringer)
                    stringer = stringer.rstrip()
                    stringer = self.utilities._reservedVariables(
                        stringer,variable_set)

                    regexer = r'{{%s}}' % params

                    # Замена в шаблоне ключевых слов {{слово}} на значения из словаря-указателя
                    for index, string_tmpl in enumerate(tmpl):
                        if regexer in string_tmpl:
                            whereis_params = string_tmpl.find(regexer)

                            adder_tab = string_tmpl[:whereis_params]
                            check_space_symbol = re.match(r"\s+$", adder_tab)
                            if stringer != 'None':
                                if check_space_symbol:
                                    tmpp = ("\n%s" % adder_tab).join(
                                        stringer.split('\n'))

                                    tmpl[index] = string_tmpl.replace(
                                        r'{{%s}}' % params, tmpp)
                                else:
                                    tmpl[index] = string_tmpl.replace(
                                        r'{{%s}}' % params, stringer)

                # Для отключения устаревших или неиспользуемых шаблонированных переменных
                tmpl = self._delete_unusing_templates(
                    tmpl, osname, file_name, directory_tmpl)
                # запись щаблона
                open(directory_result / file_name, 'w',
                     encoding=self.encoding).write(tmpl)

        print("#### Выбранная ОС: %s" % osname)
        print('#####################################')
        print('#### Создание успешно завершено! ####')
        print('#####################################')

    def get_yaml_file_on_operation_name(self,osname:str, path_to_yamls:pathlib.Path,variables:list = [])->None:
        """Получение YAML файл отдельно выбранной ОС
        Args:
            osname (str): Имя операционный системы
            path_to_yamls (pathlib.Path): Путь до файла-указателя, yaml

        Returns:
            _type_: Нет возврата, только запись в файл содержимое yaml по выбранной ОС
        """
        one_os = self.dictionary.get('DEFAULT',{})
        one_os.update(self.dictionary[osname])
        
        # Получение всех параметров из YAML
        allParams = []
        for _os in self.dictionary:
            allParams.extend(self.dictionary[_os].keys())
        allParams = list(set(allParams))
        
        # Превращение в пустые строки неиспользуемых параметров, и тех, что имеют значение Null
        for param in allParams:
            if param not in one_os:
                one_os[param]=''
            elif param in one_os:
                valParam = one_os[param]
                if valParam == None:
                    one_os[param]=''
                if type(valParam) is str:
                    one_os[param] = self.utilities._reservedVariables(one_os[param],variables)

        
        # Удаление ненужного параметра с перечислением классов
        if '(*)' in one_os:
            del one_os['(*)']

        # TODO: вернуть > и |
        name_file = osname.lower()
        if not path_to_yamls.exists(): path_to_yamls.mkdir()
        with open(path_to_yamls / f'{name_file}_export.yaml', 'wb') as yml:
            depYaml.dump(one_os,yml,encoding='utf-8',allow_unicode=True,line_break=True,indent=4)

        print(f'Для {osname} был выполнен экспорт YAML-файла в {path_to_yamls}')
        return


def get_pointer_dict(pointer_file:pathlib.Path,os_name:str):
        pointer_dict = Utils().loadYaml(pointer_file)
        pointer_dict = ExtendedDict(pointer_dict, pointer_file)
        pointer_dict.check_dublicate_values_to_one_collection()
        pointer_dict.check_dublicate_values_between()
        pointer_dict.check_availability_os(os_name)
        pointer_dict.checking_inheritance(os_name)
        pointer_dict.update_dict_default_values(os_name)
        pointer_dict.finder_links(os_name)
        return pointer_dict

def start(options):
    if not options.action:
        return
    logging.basicConfig(
        format='%(asctime)s | %(levelname)s ::: %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.DEBUG if options.debug else logging.WARNING)

    # global variables
    ROOT_PATH = pathlib.Path(__file__).parent.absolute()
    POINTER_FILE = ROOT_PATH / options.pointer_path

    if options.action == 'get-os-yaml':
        """Для получения YAML файл из файла-указателя по конкретному вендору
        """
        OS_NAME = options.os
        PATH_TO_YAMLS = ROOT_PATH / 'yamls'

        for _os in OS_NAME:
            osName = _os.upper()
            pointer_dict = get_pointer_dict(POINTER_FILE,osName)
            pointer_dict.get_yaml_file_on_operation_name(
                osName,
                PATH_TO_YAMLS,
                options.variable)
            del pointer_dict
        
        print(f'Для {OS_NAME} был выполнен экспорт YAML-файла в {PATH_TO_YAMLS}')

    if options.action == 'template':
        """Для постановки значений из файла-указателя в шаблоны
        """
        OS_NAME = options.os.upper()
        pointer_dict = get_pointer_dict(POINTER_FILE,OS_NAME)
        PATH_TO_TEMPLATES = ROOT_PATH / options.templates_path
        PATH_TO_RESULTS = ROOT_PATH / options.results_path
        pointer_dict.create_from_template(OS_NAME,
            PATH_TO_TEMPLATES, PATH_TO_RESULTS, exclude_files=[POINTER_FILE],variable_set=options.variable)


if '__main__' == __name__:
    parser = argparse.ArgumentParser(description='Генератор шаблонов',
                                     epilog='Программа, создающая на основе шаблонов и файла-указателя, \
        новые файлы, в которых могут быть подставлены значения, \
        в зависимости от сущности, которая используется в файле-указателе', add_help=False,
        prog=TEMPLER_PROG_NAME)
    parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                        help='Показывает доступные команды')
    parser.add_argument('--version', action='version', version='%(prog)s ' + TEMPLER_VERSION,
                        help='Показывает версию утилиты')

    action = parser.add_subparsers(dest='action', required=True)
    
    subparser = action.add_parser('template',add_help=False)
    subparser.add_argument('--os', type=str, required=True,
                        help='Имя сущности, которая используется в файл-указателе')
    subparser.add_argument('-d', '--debug', action='store_true', required=False,
                        help='Включить режим отладки')
    subparser.add_argument('-v', '--variable', nargs="+", type=str, required=False,
                        help='Добавить переменную для использования в YAML-файле (например, -v VAR=5 or -v VAR1=5 VAR2=5)')
    subparser.add_argument('-tl', '--templates_path', type=pathlib.Path,
                        required=True, help='Путь, где расположены файлы-шаблонов')
    subparser.add_argument('-rt', '--results_path', type=pathlib.Path,
                        required=True, help='Путь, куда сохранять результаты шаблонизации')
    subparser.add_argument('-p', '--pointer_path', type=pathlib.Path,
                        required=False, help='Путь, где расположен файл-указатель (pointer.yaml) По умолчанию программа ищет файл, расположенный в одной директории со скриптом', default='pointer.yaml')
    subparser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                        help='Показывает доступные команды')


    subparser = action.add_parser('get-os-yaml',add_help=False)
    subparser.add_argument('--os', type=str, required=True,
                        help='Имя сущности, которая используется в файл-указателе',nargs='+')
    subparser.add_argument('-d', '--debug', action='store_true', required=False,
                        help='Включить режим отладки')
    subparser.add_argument('-v', '--variable', nargs="+", type=str, required=False,
                        help='Добавить переменную для использования в YAML-файле (например, -v VAR=5 or -v VAR1=5 VAR2=5)')
    subparser.add_argument('-p', '--pointer_path', type=pathlib.Path,
                        required=False, help='Путь, где расположен файл-указатель (pointer.yaml) По умолчанию программа ищет файл, расположенный в одной директории со скриптом', default='pointer.yaml')
    subparser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                        help='Показывает доступные команды')
    

    start(parser.parse_args())