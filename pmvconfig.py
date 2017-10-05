#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" This file is part of PhotoMV.

    PhotoMV is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    PhotoMV is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with PhotoMV.  If not, see <http://www.gnu.org/licenses/>."""


import os, os.path
import sys
from locale import getdefaultlocale
from configparser import RawConfigParser, Error as ConfigParserError
from collections import namedtuple
import shutil

from pmvcommon import *
from pmvtemplates import *

workmodemsgs = namedtuple('workmodemsgs', 'errmsg statmsg')


ENCODING = getdefaultlocale()[1]
if not ENCODING:
    ENCODING = sys.getfilesystemencoding()


class PMVRawConfigParser(RawConfigParser):
    def getstr(self, secname, varname):
        """В отличие от RawConfigParser.get возвращает пустую строку
        при отсутствии переменной varname в секции secname."""

        if self.has_option(secname, varname):
            return self.get(secname, varname).strip()
        else:
            return ''


DEFAULT_CONFIG = '''[paths]
src-dirs = /media/user/NIKON D70/DCIM
dest-dir = ~/docs/raw

[options]
if-exists = skip

[aliases]
NIKON D70 = nd70
Canon EOS 5D Mark III = c5d3

[templates]
* = {year}/{month}/{day}/raw/{type}{year}{month}{day}_{number}
Canon EOS 5D Mark III = {year}/{month}/{day}/raw/{type}{year}{month}{day}_{alias}_{number}
'''


class Environment():
    """Все настройки"""

    MODE_MOVE = 'photomv'
    MODE_MOVE_GUI = 'photomvg'
    MODE_COPY = 'photocp'
    MODE_COPY_GUI = 'photocpg'

    CFG_FILE = 'settings.ini'

    class Error(Exception):
        pass

    FEXIST_SKIP, FEXIST_RENAME, FEXIST_OVERWRITE = range(3)

    FEXIST_OPTIONS = {'skip':FEXIST_SKIP,
                      's':FEXIST_SKIP,
                      'rename':FEXIST_RENAME,
                      'r':FEXIST_RENAME,
                      'overwrite':FEXIST_OVERWRITE,
                      'o':FEXIST_OVERWRITE}

    SEC_PATHS = 'paths'
    OPT_SRC_DIRS = 'src-dirs'
    OPT_DEST_DIR = 'dest-dir'

    SEC_OPTIONS = 'options'
    OPT_IF_EXISTS = 'if-exists'
    OPT_SHOW_SRC_DIR = 'show-src-dir'

    SEC_TEMPLATES = 'templates'
    DEFAULT_TEMPLATE_NAME = '*'

    SEC_ALIASES = 'aliases'

    E_BADVAL = 'Неправильное значение параметра "%s" в секции "%s" файла настроек "%s" - %s'
    E_BADVAL2 = 'Неправильное значение параметра "%s" в секции "%s" файла настроек "%s"'
    E_DUPVAL = 'Имя параметра "%s" использовано более одного раза в секции "%s" файла настроек "%s"'
    E_NOVAL = 'Отсутствует значение параметра "%s" в секции "%s" файла настроек "%s"'
    E_NOSECTION = 'В файле настроек "%s" отсутствует секция "%s"'
    E_CONFIG = 'Ошибка обработки файла настроек - %s'
    E_CMDLINE = 'параметр %d командной строки: %s'

    @staticmethod
    def detect_work_mode(arg0):
        """Определение режима работы по имени исполняемого файла программы arg0
        (берется из sys.argv[0]).

        Возвращает кортеж из двух булевских значений:
        1. режим работы - перемещение (True) или копирование (False);
        2. режим интерфейса - GTK (True) или консоль (False).

        В случае ошибки (не удалось определить режим) возвращает кортеж
        из двух None."""

        #
        # определяем, кто мы такое
        #
        bname = os.path.basename(arg0)

        # имя того, что запущено, в т.ч. если вся куча засунута
        # в архив ZIP

        bnamecmd = os.path.splitext(bname)[0].lower()

        if bnamecmd in (Environment.MODE_MOVE, Environment.MODE_MOVE_GUI):
            modeMoveFiles = True
        elif bnamecmd in (Environment.MODE_COPY, Environment.MODE_COPY_GUI):
            modeMoveFiles = False
        else:
            raise Environment.Error('Меня зовут %s, и я не знаю, что делать.' % bname)

        return (modeMoveFiles, bnamecmd in (Environment.MODE_MOVE_GUI, Environment.MODE_COPY_GUI))

    def __init__(self, args, workModeMove, guiMode):
        """Разбор командной строки, поиск и загрузка файла конфигурации.

        args            - аргументы командной строки (список строк)
        workModeMove    - режим работы - перемещение (True) или копирование (False)
        guiMode         - режим интерфейса - GTK (True) или консоль (False)

        В случае ошибок генерирует исключения.
        Исключение Environment.Error должно обрабатываться в программе."""

        #
        # параметры
        #
        self.modeMoveFiles = workModeMove
        self.GUImode = guiMode

        if workModeMove:
            self.modeMessages = workmodemsgs('переместить', 'перемещено')
            self.modeFileOp = shutil.move
        else:
            self.modeMessages = workmodemsgs('скопировать', 'скопировано')
            self.modeFileOp = shutil.copy

        # каталог, из которого копируются (или перемещаются) изображения
        self.sourceDirs = []

        # каталог, в который копируются (или перемещаются) изображения
        self.destinationDir = None

        # что делать с файлами, которые уже есть в каталоге-приемнике
        self.ifFileExists = self.FEXIST_RENAME

        # показывать ли каталоги-источники
        self.showSrcDir = False

        # сокращенные псевдонимы камер
        # ключи словаря - названия камер, соответствующие соотв. полю EXIF
        # значения - строки псевдонимов
        self.aliases = {}

        # индивидуальные шаблоны
        # общий шаблон по умолчанию также будет воткнут сюда при
        # вызове __read_config_templates()
        # ключи словаря - названия камер из EXIF, или "*" для общего
        # шаблона;
        # значения словаря - экземпляры класса FileNameTemplate
        self.templates = {}

        #
        # ищем файл конфигурации
        #
        self.configPath = self.__get_config_path(args[0])

        cfg = PMVRawConfigParser()

        with open(self.configPath, 'r', encoding=ENCODING) as f:
            try:
                cfg.read_file(f)
            except ConfigParserError as ex:
                raise self.Error(self.E_CONFIG % str(ex))

        # прочие исключения пока исключения не проверяем.
        # в документации об обработке ошибок чтения что-то мутно

        #
        # выгребаем настройки
        #

        if cfg.has_section(self.SEC_PATHS):
            self.__read_config_paths(cfg)
        else:
            raise self.Error(self.E_NOSECTION % (self.configPath, self.SEC_PATHS))

        if cfg.has_section(self.SEC_OPTIONS):
            self.__read_config_options(cfg)
        else:
            raise self.Error(self.E_NOSECTION % (self.configPath, self.SEC_OPTIONS))

        #
        # сокращённые имена камер
        #

        if cfg.has_section(self.SEC_ALIASES):
            self.__read_config_aliases(cfg)

        #
        # шаблоны
        #

        if cfg.has_section(self.SEC_TEMPLATES):
            self.__read_config_templates(cfg)

        #
        # ...а вот теперь - разгребаем командную строку, т.к. ее параметры
        # перекрывают файл настроек
        #

        for argnum, arg in enumerate(args[1:], 1):
            if arg.startswith('-'):
                if arg in ('-g', '--gui'):
                    self.GUImode = True
                elif arg in ('-n', '--no-gui'):
                    self.GUImode = False
                else:
                    raise self.Error(self.E_CMDLINE % (argnum, 'параметр "%s" не поддерживается' % arg))
            else:
                raise self.Error(self.E_CMDLINE % (argnum, 'ненужное имя файла'))

    def __read_config_paths(self, cfg):
        """Разбор секции paths файла настроек"""

        #
        # каталоги с исходными файлами
        #

        rawSrcDirs = map(lambda s: s.strip(), cfg.getstr(self.SEC_PATHS, self.OPT_SRC_DIRS).split(':'))
        srcDirHashes = set()

        for ixsd, srcdir in enumerate(rawSrcDirs, 1):
            if srcdir:
                # пустые строки пропускаем - опухнешь на каждую мелочь ругаться

                srcdir = validate_path(srcdir)

                # пути добавляем во внутренний список при двух условиях:
                # 1. путь существует и указывает на каталог
                # 2. путь еще не добавлен в список;
                #    проверка на повторы - РЕГИСТРО-ЗАВИСИМАЯ, ибо *nix
                if os.path.exists(srcdir):
                    if not os.path.isdir(srcdir):
                        raise self.Error(self.E_BADVAL % (self.OPT_SRC_DIRS, self.SEC_PATHS, self.configPath,
                            'путь "%s" указывает не на каталог' % srcdir))

                    h = hash(srcdir)
                    if h not in srcDirHashes:
                        srcDirHashes.add(h)
                        self.sourceDirs.append(srcdir)

        if not self.sourceDirs:
            raise self.Error(self.E_BADVAL % (self.OPT_SRC_DIRS, self.SEC_PATHS, self.configPath, 'не указано ни одного существующего исходного каталога'))

        #
        # каталог назначения
        #

        self.destinationDir = cfg.getstr(self.SEC_PATHS, self.OPT_DEST_DIR)

        if not self.destinationDir:
            raise self.Error(self.E_NOVAL % (self.OPT_DEST_DIR, self.SEC_PATHS, self.configPath))

        self.destinationDir = validate_path(self.destinationDir)

        if not os.path.exists(self.destinationDir):
            raise self.Error(self.E_BADVAL % (self.OPT_DEST_DIR, self.SEC_PATHS, self.configPath,
                'путь "%s" не существует' % self.destinationDir))

        if not os.path.isdir(self.destinationDir):
            raise self.Error(self.E_BADVAL % (self.OPT_DEST_DIR, self.SEC_PATHS, self.configPath,
                'путь "%s" указывает не на каталог' % self.destinationDir))

        for sdir in self.sourceDirs:
            if os.path.samefile(sdir, self.destinationDir):
                raise self.Error(self.E_BADVAL % (self.OPT_DEST_DIR, self.SEC_PATHS, self.configPath,
                    'каталог назначения совпадает с одним из исходных каталогов'))

    def __read_config_options(self, cfg):
        """Разбор секции options файла настроек"""

        #
        # if-exists
        #
        ieopt = cfg.getstr(self.SEC_OPTIONS, self.OPT_IF_EXISTS).lower()
        if not ieopt:
            raise self.Error(self.E_NOVAL % (self.OPT_IF_EXISTS, self.SEC_OPTIONS, self.configPath))

        if ieopt not in self.FEXIST_OPTIONS:
            raise self.Error(self.E_BADVAL2 % (self.OPT_IF_EXISTS, self.SEC_OPTIONS, self.configPath))

        self.ifFileExists = self.FEXIST_OPTIONS[ieopt]

        #
        # show-src-dir
        #
        self.showSrcDir = cfg.getboolean(self.SEC_OPTIONS, self.OPT_SHOW_SRC_DIR, fallback=False)

    def __read_config_aliases(self, cfg):
        """Разбор секции aliases файла настроек"""

        anames = cfg.options(self.SEC_ALIASES)

        for aname in anames:
            astr = cfg.getstr(self.SEC_ALIASES, aname)

            if not astr:
                raise self.Error(self.E_NOVAL % (aname, self.SEC_ALIASES, self.configPath))

            # проверку на повтор не делаем - RawConfigParser ругнётся раньше на одинаковые опции
            self.aliases[aname.lower()] = normalize_filename(astr)

    def __read_config_templates(self, cfg):
        """Разбор секции templates файла настроек"""

        tnames = cfg.options(self.SEC_TEMPLATES)

        for tname in tnames:
            tstr = cfg.getstr(self.SEC_TEMPLATES, tname)

            if not tstr:
                raise self.Error(self.E_NOVAL % (tname, self.SEC_TEMPLATES, self.configPath))

            tplname = tname.lower()

            # проверку на повтор не делаем - RawConfigParser ругнётся раньше на одинаковые опции
            try:
                self.templates[tplname] = FileNameTemplate(tstr)
            except Exception as ex:
                raise self.Error(self.E_BADVAL % (tname, self.SEC_TEMPLATES, self.configPath, str(ex)))

        # если в файле настроек не был указан общий шаблон с именем "*",
        # то добавляем в templates встроенный шаблон pmvtemplates.defaultFileNameTemplate
        # под именем "*"

        if self.DEFAULT_TEMPLATE_NAME not in self.templates:
            self.templates[self.DEFAULT_TEMPLATE_NAME] = defaultFileNameTemplate

    def __get_config_path(self, me):
        """Поиск файла конфигурации.

        При отсутствии - создание файла со значениями по умолчанию
        и завершение работы."""

        cfg = os.path.join(os.path.split(me)[0], self.CFG_FILE)

        if not os.path.exists(cfg):
            cfgdir = os.path.expanduser('~/.config/photomv')
            cfg = os.path.join(cfgdir, self.CFG_FILE)

            if not os.path.exists(cfg):
                # создаём файл настроек

                make_dirs(cfgdir, self.Error)

                try:
                    with open(cfg, 'w+', encoding=ENCODING) as f:
                        f.write(DEFAULT_CONFIG)
                except OSError as ex:
                    raise self.Error('Не удалось создать новый файл настроек "%s" - %s' % (cfg, str(ex)))

                raise self.Error('Файл настроек не найден, создан новый файл "%s".\nДля продолжения работы файл настроек должен быть отредактирован.' % cfg)

        return cfg

    def get_template(self, cameraModel):
        """Получение экземпляра pmvtemplates.FileNameTemplate для
        определённой камеры.

        cameraModel - название модели из метаданных файла
                      (pmvmetadata.FileMetadata.fields[pmvmetadata.MODEL]),
                      пустая строка, или None;
                      в последних двух случаях возвращает общий шаблон
                      из файла настроек, если он указан, иначе возвращает
                      встроенный общий шаблон программы."""

        if cameraModel:
            cameraModel = cameraModel.lower()

            if cameraModel in self.templates:
                return self.templates[cameraModel]

        return self.templates[self.DEFAULT_TEMPLATE_NAME]

    def __str__(self):
        return '''modeMoveFiles = %s
GUImode = %s
modeMessages = %s
modeFileOp = %s
sourceDirs = %s
destinationDir = "%s"
ifFileExists = %d
showSrcDir = %s
aliases = %s
templates = %s''' % (self.modeMoveFiles, self.GUImode,
    self.modeMessages,
    self.modeFileOp,
    str(self.sourceDirs), self.destinationDir,
    self.ifFileExists,
    self.showSrcDir,
    self.aliases,
    ', '.join(map(str, self.templates.values())))


if __name__ == '__main__':
    print('[%s test]' % __file__)

    try:
        mode, gui = Environment.detect_work_mode('photocpg.py')
        env = Environment(sys.argv, mode, gui)
    except Environment.Error as ex:
        print('** %s' % str(ex))
        exit(1)

    print(env)
    #tpl = env.get_template('')
    #print('template:', tpl, repr(tpl))
