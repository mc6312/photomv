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
import datetime
import csv
import argparse

from pmvcommon import *
from pmvtemplates import *
from pmvmetadata import FileMetadata, FileTypes


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


class PMVLogger():
    """Журнал операций PhotoMV.
    Хранит данные в формате CSV.
    Разделители полей - ";", поля могут быть заключены в кавычки (если
    содержат символ разделителя и/или перевод строки).
    Записи сохраняются с помощью стандартного питоньего модуля csv,
    и, соответственно, с его же помощью могут быть и прочитаны.
    Количество полей в текущей верии - пять:
    1: дата/время в формате YYYY-MM-DD HH:MM:SS,
    2: ключевое слово операции (см. KW_xxx),
    3: True или False - результат выполнения операции,
    4 и 5: параметры, зависящие от операции."""

    # метка запуска (сообщение с ней вставляется автоматически при вызове метода open)
    # 3й параметр - всегда True, 4й и 5й параметры - пустые строки
    KW_START = 'start'
    # метка останова (сообщение с ней вставляется автоматически при вызове метода close)
    # 3й параметр - всегда True, 4й и 5й параметры - пустые строки
    KW_STOP = 'stop'
    # информационное сообщение
    # 3й параметр - всегда True, 4й параметр - текст сообщения, 5й - пустая строка
    KW_MSG = 'msg'
    # сообщение об ошибке
    # 3й параметр - всегда False, 4й параметр - текст сообщения, 5й - пустая строка
    KW_ERROR = 'error'
    # сообщение о попытке копирования файла
    # 3й параметр - результат копирования, 4й параметр - исходное имя, 5й - имя назначения
    KW_CP = 'cp'
    # сообщение о попытке перемещения файла
    # 3й параметр - результат перемещения, 4й параметр - исходное имя, 5й - новое имя
    KW_MV = 'mv'
    # сообщение о попытке создания каталога
    # 3й параметр - результат операции, 4й параметр - путь к новому каталогу, 5й - пустая строка
    KW_MKDIR = 'mkdir'

    LOG_FNAME = 'operations.log'
    LOG_FNAME_OLD = LOG_FNAME + '.old'

    LOG_TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'

    def __init__(self, logDir, maxLogSizeMB):
        """logDir       - полный путь к каталогу с файлами журналов,
        maxLogSizeMB    - максимальный размер файла журнала в мегабайтах
                          (для ротации)."""

        self.logDir = logDir
        self.logPath = os.path.join(self.logDir, self.LOG_FNAME)
        self.logOldPath = os.path.join(self.logDir, self.LOG_FNAME_OLD)

        self.maxLogSize = maxLogSizeMB * 1024 * 1024

        # файл, куда пишется журнал; значение присваивается из метода open()
        self.logf = None

        # после вызова метода open() - экземпляр csv.writer
        self.logwriter = None

    def __repr__(self):
        """Для отладки"""

        return '%s(logDir="%s", logPath="%s", maxLogSize=%d)' % (
            self.__class__.__name__,
            self.logDir,
            self.logPath,
            self.maxLogSize)

    def __rotate_logs(self):
        """наколенная ротация файлов журналов"""

        if self.logf is not None:
            raise EnvironmentError('ротация открытого файла журнала невозможна')

        if os.path.exists(self.logPath):
            lfs = os.stat(self.logPath).st_size

            if lfs > self.maxLogSize:
                if os.path.exists(self.logOldPath):
                    os.remove(self.logOldPath)
                    os.rename(self.logPath, self.logOldPath)

    def open(self):
        if self.logf is None:
            self.__rotate_logs()

            self.logf = open(self.logPath, 'a')
            self.logwriter = csv.writer(self.logf, delimiter=';', dialect=csv.excel)

            self.write(None, self.KW_START, True, '', '')

    E_LOG_NOT_OPEN = 'файл журнала "%s" не открыт'

    def close(self):
        if self.logf is None:
            raise EnvironmentError(self.E_LOG_NOT_OPEN % self.logPath)
        else:
            self.write(None, self.KW_STOP, True, '', '')

            self.logwriter = None
            self.logf.close()
            self.logf = None

            self.__rotate_logs()

    def write(self, timestamp, operation, result, param1, param2):
        """Запись операции в журнал.
        timestamp   - экземпляр datetime.datetime или None,
                      в последнем случае используется текущее время
        operation   - строка, KW_xxx
        result      - булевское значение, результат операции
        param1 и param2 зависят от операции."""

        if self.logf is None:
            raise EnvironmentError(self.E_LOG_NOT_OPEN % self.logPath)

        if timestamp is None:
            timestamp = datetime.datetime.now()

        self.logwriter.writerow((timestamp.strftime(self.LOG_TIMESTAMP_FORMAT),
            operation, str(result), param1, param2))

    def write_msg(self, timestamp, message):
        self.write(timestamp, self.KW_MSG, True, message, '')

    def write_error(self, timestamp, message):
        self.write(timestamp, self.KW_ERROR, False, message, '')


DEFAULT_CONFIG = '''[paths]
src-dirs = /media/user/NIKON D70/DCIM
dest-dir = ~/docs/raw

[options]
if-exists = skip

[aliases]
NIKON D70 = nd70
Canon EOS 5D Mark III = c5d3

[templates]
* = {year}/{month}/{day}/{longtype}/{type}{year}{month}{day}_{number}
Canon EOS 5D Mark III = {year}/{month}/{day}/raw/{type}{year}{month}{day}_{alias}_{number}
'''


class Environment():
    """Все настройки"""

    MODE_MOVE = 'photomv'
    MODE_COPY = 'photocp'

    CFG_FILE = 'settings.ini'

    class Error(Exception):
        pass

    # эхехех, сюда бы dataclass из Python 3.7...
    class SourceDir:
        __slots__ = 'path', 'ignore'

        def __init__(self, path, ignore=False):
            self.path = path
            self.ignore = ignore

        def __repr__(self):
            # для отладки
            return '%s(path="%s", ignore=%s)' % (self.__class__.__name__, self.path, self.ignore)

    FEXIST_SKIP, FEXIST_RENAME, FEXIST_OVERWRITE = range(3)

    FEXIST_OPTIONS = {'skip':FEXIST_SKIP,
                      's':FEXIST_SKIP,
                      'rename':FEXIST_RENAME,
                      'r':FEXIST_RENAME,
                      'overwrite':FEXIST_OVERWRITE,
                      'o':FEXIST_OVERWRITE}

    FEXISTS_OPTIONS_STR = {FEXIST_SKIP:'skip',
        FEXIST_RENAME:'rename',
        FEXIST_OVERWRITE:'overwrite'}

    FEXISTS_DISPLAY = ('пропустить', # FEXIST_SKIP
        'переименовать', # FEXIST_RENAME
        'перезаписать')  # FEXIST_OVERWRITE

    SEC_PATHS = 'paths'
    OPT_SRC_DIRS = 'src-dirs'
    OPT_DEST_DIR = 'dest-dir'

    SEC_OPTIONS = 'options'
    OPT_IF_EXISTS = 'if-exists'
    OPT_SHOW_SRC_DIR = 'show-src-dir'
    OPT_MAX_LOG_SIZE = 'max-log-size'

    #FileMetadata.FILE_TYPE_IMAGE, FILE_TYPE_RAW_IMAGE, FILE_TYPE_VIDEO
    OPT_KNOWN_FILE_TYPES = ('known-image-types',
        'known-raw-image-types',
        'known-video-types')

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

    DEFAULT_MAX_LOG_SIZE = 10 # максимальный размер файла журнала в мегабайтах

    def setup_work_mode(self):
        """Вызывать после изменения workModeMove"""

        if self.modeMoveFiles:
            self.modeMessages = workmodemsgs('переместить', 'перемещено')
            self.modeFileOp = shutil.move
        else:
            self.modeMessages = workmodemsgs('скопировать', 'скопировано')
            self.modeFileOp = shutil.copy

    def __init__(self):
        """Поиск и загрузка файла конфигурации, после - разбор командной
        строки.

        В случае ошибок генерирует исключения."""

        #
        # параметры
        #
        self.modeMoveFiles = None

        self.modeMessages = None
        self.modeFileOp = None

        # каталоги, из которых копируются (или перемещаются) изображения
        # список экземпляров Environment.SourceDir
        self.sourceDirs = []

        # каталог, в который копируются (или перемещаются) изображения
        self.destinationDir = None

        # поддерживаемые типы файлов (по расширениям)
        self.knownFileTypes = FileTypes()

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

        # максимальный размер файла журнала в мегабайтах
        self.maxLogSizeMB = self.DEFAULT_MAX_LOG_SIZE


        #
        # ищем файл конфигурации
        #
        self.configPath = self.__get_config_path(sys.argv[0])
        self.cfg = PMVRawConfigParser()

        with open(self.configPath, 'r', encoding=ENCODING) as f:
            try:
                self.cfg.read_file(f)
            except ConfigParserError as ex:
                raise self.Error(self.E_CONFIG % str(ex))

        # прочие исключения пока исключения не проверяем.
        # в документации об обработке ошибок чтения что-то мутно

        #
        # выгребаем настройки
        #

        if self.cfg.has_section(self.SEC_PATHS):
            self.__read_config_paths()
        else:
            raise self.Error(self.E_NOSECTION % (self.configPath, self.SEC_PATHS))

        if self.cfg.has_section(self.SEC_OPTIONS):
            self.__read_config_options()
        else:
            raise self.Error(self.E_NOSECTION % (self.configPath, self.SEC_OPTIONS))

        #
        # сокращённые имена камер
        #

        if self.cfg.has_section(self.SEC_ALIASES):
            self.__read_config_aliases()

        #
        # шаблоны
        #

        if self.cfg.has_section(self.SEC_TEMPLATES):
            self.__read_config_templates()

        #
        # журналирование операций
        #

        self.logger = PMVLogger(self.__get_log_directory(), self.maxLogSizeMB)

        #
        # ...а вот теперь - разгребаем командную строку, т.к. ее параметры
        # перекрывают файл настроек
        #

        self.__detect_work_mode()
        self.__parse_cmdline_options()

        if self.modeMoveFiles is None:
            raise self.Error('Меня зовут %s, и я не знаю, что делать.' % bname)

        #
        # проверяем, все ли нужные параметры указаны
        #
        if not self.sourceDirs:
            raise self.Error('не указано ни одного существующего исходного каталога')

        # каталог назначения проверяем перед началом работы с файлами,
        # т.к. его может потребоваться создать именно тогда

        # минимальное причёсывание
        if self.destinationDir:
            self.destinationDir = validate_path(self.destinationDir)

            if os.path.exists(self.destinationDir) and not os.path.isdir(self.destinationDir):
                raise self.Error('путь "%s" указывает не на каталог' % self.destinationDir)

        #
        self.setup_work_mode()

    def __detect_work_mode(self):
        """Предварительное определение режима работы
        (перемещение/копирование) по имени исполняемого файла."""

        #
        # определяем, кто мы такое
        #
        bname = os.path.basename(sys.argv[0])

        # имя того, что запущено, в т.ч. если вся куча засунута
        # в архив ZIP

        bnamecmd = os.path.splitext(bname)[0].lower()

        if bnamecmd == self.MODE_MOVE:
            self.modeMoveFiles = True
        elif bnamecmd == self.MODE_COPY:
            self.modeMoveFiles = False
        else:
            # ругаться будем потом, если режим не указан в командной строке
            self.modeMoveFiles = None

    def __parse_cmdline_options(self):
        """Разбор аргументов командной строки"""

        aparser = argparse.ArgumentParser(description='Поиск в каталогах-источниках изображений и видеофайлов, их перемещение\
            (или копирование) в каталог-приемник.',
            epilog='Если в командной строке указано от одного до нескольких каталогов, то последний (или единственный)\
            является каталогом назначения, а прочие - каталогами-источниками.\nПараметры из командной строки имеют\
            приоритет перед параметрами из файла настроек.')

        aparser.add_argument('directory', help='каталог назначения и/или каталог-источник',
            action='append', nargs='*')

        grpmode = aparser.add_mutually_exclusive_group()
        grpmode.add_argument('-c', '--copy', help='режим копирования файлов',
            action='store_false', dest='movemode', default=self.modeMoveFiles)
        grpmode.add_argument('-m', '--move', help='режим перемещения файлов',
            action='store_true', dest='movemode', default=self.modeMoveFiles)

        aparser.add_argument('-e', '--if-exists', help='поведение при совпадении имён файлов в каталоге назначения',
            action='store', nargs='?', dest='ifexist',
            choices=self.FEXIST_OPTIONS.keys(),
            default=self.FEXISTS_OPTIONS_STR[self.ifFileExists])

        args = aparser.parse_args()

        # т.к. ArgumentParser хранит обычные параметры как список списков, извращаемся:

        def __expand_list(l):
            r = []

            for e in l:
                if isinstance(e, list):
                    r += __expand_list(e)
                else:
                    r.append(e)

            return r

        adirs = __expand_list(args.directory)

        if adirs:
            self.destinationDir = adirs[-1]

            if len(adirs) > 1:
                # в командной строке есть каталоги-источники - они заменяют указанные в конфиге!
                self.sourceDirs.clear()

                for srcdir in adirs[:-1]:
                    self.__add_src_dir(srcdir, False, False)

    def __add_src_dir(self, path, ignore, fromconfig):
        """Добавление каталога в список каталогов-источников.

        path        - путь к каталогу,
        ignore      - булевский параметр (см. класс SourceDir),
        fromconfig  - True, если каталог добавляется из файла настроек
                      (см. ниже варианты сообщений об ошибках)."""

        path = validate_path(path)

        # путь добавляем во внутренний список, если он не совпадает
        # с каким-то из уже добавленных;
        # существование каталога будет проверено при обработке файлов

        if self.same_src_dir(path):
            es = 'путь к каталогу-источнику "%s" совпадает с одним из уже указанных' % srcdir

            if fromconfig:
                es = self.E_BADVAL % (self.OPT_SRC_DIRS, self.SEC_PATHS, self.configPath, es)

            raise self.Error(es)

        self.sourceDirs.append(self.SourceDir(path, ignore))

    def __read_config_paths(self):
        """Разбор секции paths файла настроек"""

        #
        # каталоги с исходными файлами
        #

        rawSrcDirs = map(lambda s: s.strip(), self.cfg.getstr(self.SEC_PATHS, self.OPT_SRC_DIRS).split(':'))

        for ixsd, srcdir in enumerate(rawSrcDirs, 1):
            if srcdir:
                # пустые строки пропускаем - опухнешь на каждую мелочь ругаться

                if srcdir.startswith('-'):
                    srcdirignore = True
                    srcdir = srcdir[1:]
                else:
                    srcdirignore = False

                self.__add_src_dir(srcdir, srcdirignore, True)

        # наличие хоть одного каталога-источника проверяется в конце __init__

        #
        # каталог назначения
        #

        self.destinationDir = self.cfg.getstr(self.SEC_PATHS, self.OPT_DEST_DIR)

        # правильность указания каталога назначения проверяется в конце __init__

    def check_dest_is_same_with_src_dir(self):
        """Проверка, не является ли каталог назначения одним из каталогов-
        источников.

        Возвращает True, если случилась такая досада..."""
        return self.same_src_dir(self.destinationDir)

    def same_src_dir(self, dirname):
        """Возвращает True, если каталог dirname совпадает с одним из
        каталогов списка self.sourceDirs."""

        for sd in self.sourceDirs:
            if same_dir(sd.path, dirname):
                return True

        return False

    def __read_config_options(self):
        """Разбор секции options файла настроек"""

        #
        # if-exists
        #
        ieopt = self.cfg.getstr(self.SEC_OPTIONS, self.OPT_IF_EXISTS).lower()
        if not ieopt:
            raise self.Error(self.E_NOVAL % (self.OPT_IF_EXISTS, self.SEC_OPTIONS, self.configPath))

        if ieopt not in self.FEXIST_OPTIONS:
            raise self.Error(self.E_BADVAL2 % (self.OPT_IF_EXISTS, self.SEC_OPTIONS, self.configPath))

        self.ifFileExists = self.FEXIST_OPTIONS[ieopt]

        #
        # show-src-dir
        #
        self.showSrcDir = self.cfg.getboolean(self.SEC_OPTIONS, self.OPT_SHOW_SRC_DIR, fallback=False)

        #
        # known-*-types
        #
        for ixopt, optname in enumerate(self.OPT_KNOWN_FILE_TYPES):
            kts = filter(None, self.cfg.getstr(self.SEC_OPTIONS, optname).lower().split(None))

            exts = set()

            for ktype in kts:
                if not ktype.startswith('.'):
                    ktype = '.%s' % ktype

                exts.add(ktype)

            self.knownFileTypes.add_extensions(ixopt, exts)

        #
        # max-log-size
        #
        mls = self.cfg.getint(self.SEC_OPTIONS, self.OPT_MAX_LOG_SIZE, fallback=self.DEFAULT_MAX_LOG_SIZE)
        if mls < 0:
            mls = self.DEFAULT_MAX_LOG_SIZE

        self.maxLogSizeMB = mls

    def __read_config_aliases(self):
        """Разбор секции aliases файла настроек"""

        anames = self.cfg.options(self.SEC_ALIASES)

        for aname in anames:
            astr = self.cfg.getstr(self.SEC_ALIASES, aname)

            if not astr:
                raise self.Error(self.E_NOVAL % (aname, self.SEC_ALIASES, self.configPath))

            # проверку на повтор не делаем - RawConfigParser ругнётся раньше на одинаковые опции
            self.aliases[aname.lower()] = normalize_filename(astr)

    def __read_config_templates(self):
        """Разбор секции templates файла настроек"""

        tnames = self.cfg.options(self.SEC_TEMPLATES)

        for tname in tnames:
            tstr = self.cfg.getstr(self.SEC_TEMPLATES, tname)

            if not tstr:
                raise self.Error(self.E_NOVAL % (tname, self.SEC_TEMPLATES, self.configPath))

            tplname = tname.lower()

            # проверку на повтор не делаем - RawConfigParser ругнётся раньше на одинаковые опции
            try:
                self.templates[tplname] = FileNameTemplate(tstr)
            except Exception as ex:
                raise self.Error(self.E_BADVAL % (tname, self.SEC_TEMPLATES, self.configPath, repr(ex)))

        # если в файле настроек не был указан общий шаблон с именем "*",
        # то добавляем в templates встроенный шаблон pmvtemplates.defaultFileNameTemplate
        # под именем "*"

        if self.DEFAULT_TEMPLATE_NAME not in self.templates:
            self.templates[self.DEFAULT_TEMPLATE_NAME] = defaultFileNameTemplate

    def __get_log_directory(self):
        """Возвращает полный путь к каталогу файлов журналов операций.
        При отсутствии каталога - создаёт его."""

        logdir = os.path.expanduser('~/.cache/photomv')
        if not os.path.exists(logdir):
            make_dirs(logdir, self.Error)

        return logdir

    def __get_config_path(self, me):
        """Поиск файла конфигурации.

        При отсутствии - создание файла со значениями по умолчанию
        и завершение работы."""

        cfgpath = os.path.join(os.path.split(me)[0], self.CFG_FILE)

        if not os.path.exists(cfgpath):
            cfgdir = os.path.expanduser('~/.config/photomv')
            cfgpath = os.path.join(cfgdir, self.CFG_FILE)

            if not os.path.exists(cfgpath):
                # создаём файл настроек

                make_dirs(cfgdir, self.Error)

                try:
                    with open(cfgpath, 'w+', encoding=ENCODING) as f:
                        f.write(DEFAULT_CONFIG)
                except OSError as ex:
                    raise self.Error('Не удалось создать новый файл настроек "%s" - %s' % (cfgpath, repr(ex)))

                raise self.Error('Файл настроек не найден, создан новый файл "%s".\nДля продолжения работы файл настроек должен быть отредактирован.' % cfgpath)

        return cfgpath

    def save(self):
        """Сохранение настроек.
        В случае ошибки генерирует исключение."""

        # секция paths
        self.cfg.set(self.SEC_PATHS, self.OPT_SRC_DIRS, ':'.join(map(lambda sd: '%s%s' % ('-' if sd.ignore else '', sd.path), self.sourceDirs)))
        self.cfg.set(self.SEC_PATHS, self.OPT_DEST_DIR, self.destinationDir)

        # секция options
        self.cfg.set(self.SEC_OPTIONS, self.OPT_IF_EXISTS, self.FEXISTS_OPTIONS_STR[self.ifFileExists])
        self.cfg.set(self.SEC_OPTIONS, self.OPT_SHOW_SRC_DIR, str(self.showSrcDir))

        # секции aliases и templates не трогаем, т.к. они из гуя не изменяются

        # сохраняем
        with open(self.configPath, 'w+', encoding=ENCODING) as f:
            self.cfg.write(f)

    def get_template(self, cameraModel):
        """Получение экземпляра pmvtemplates.FileNameTemplate для
        определённой камеры.

        cameraModel - название модели из метаданных файла
                      (pmvmetadata.FileMetadata.fields[pmvmetadata.MODEL]),
                      пустая строка, или None;
                      в последних двух случаях возвращает общий шаблон
                      из файла настроек, если он указан, иначе возвращает
                      встроенный общий шаблон программы."""

        if self.templates:
            if cameraModel:
                cameraModel = cameraModel.lower()

                # ключ в словаре шаблонов может содержать символы подстановки,
                # а потому проверяем ключи вручную!
                for tplCameraModel in self.templates:
                    if tplCameraModel == self.DEFAULT_TEMPLATE_NAME:
                        # ибо self.DEFAULT_TEMPLATE_NAME = "*", а у нас тут fnmatch
                        continue

                    if fnmatch(cameraModel, tplCameraModel):
                        return self.templates[tplCameraModel]

        # шаблон не нашёлся по названию камеры -
        # пробуем общий из настроек, если он есть
        if self.DEFAULT_TEMPLATE_NAME in self.templates:
            return self.templates[self.DEFAULT_TEMPLATE_NAME]

        # а когда совсем ничего нету - встроенный шаблон
        return defaultFileNameTemplate

    def get_template_from_metadata(self, metadata):
        """Получение экземпляра pmvtemplates.FileNameTemplate для
        определённой камеры, модель которой определяется по
        соответствующему полю metadata - экземпляра FileMetadata."""

        return self.get_template(metadata.fields[metadata.MODEL])

    def __repr__(self):
        """Для отладки"""
        return '%s(cfg = "%s", modeMoveFiles = %s, modeMessages = %s, modeFileOp = %s, sourceDirs = %s, destinationDir = "%s", ifFileExists = %s, knownFileTypes: %s, showSrcDir = %s, aliases = %s, templates = %s, maxLogSizeMB = %d, logger = "%s")' % (
            self.__class__.__name__,
            self.cfg,
            self.modeMoveFiles,
            self.modeMessages,
            self.modeFileOp,
            str(self.sourceDirs),
            self.destinationDir,
            self.FEXISTS_OPTIONS_STR[self.ifFileExists],
            self.knownFileTypes,
            self.showSrcDir,
            self.aliases,
            ', '.join(map(str, self.templates.values())),
            self.maxLogSizeMB,
            self.logger)


if __name__ == '__main__':
    print('[debugging %s]' % __file__)

    try:
        sys.argv[0] = 'photocp.py'
        #sys.argv.append('-h')
        env = Environment()
        #env.save()

    except Environment.Error as ex:
        print('** %s' % str(ex))
        exit(1)

    print(env)
    #tpl = env.get_template('')
    #print('template:', tpl, repr(tpl))

    #env.save()

    print(env.knownFileTypes.get_file_type_by_name('filename.m4v'))

    env.logger.open()
    try:
        env.logger.write(None, env.logger.KW_CP, True, 'oldfile', 'newfile')
        env.logger.write(None, env.logger.KW_MSG, True, 'some\nmessage', '')
        env.logger.write(None, env.logger.KW_MSG, True, 'some other message', '')
    finally:
        env.logger.close()
