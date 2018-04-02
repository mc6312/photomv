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
from pmvmetadata import FileMetadata


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
    OPT_KNOWN_IMAGE_TYPES = 'known-image-types'
    OPT_KNOWN_VIDEO_TYPES = 'known-video-types'

    SEC_TEMPLATES = 'templates'
    DEFAULT_TEMPLATE_NAME = '*'

    SEC_ALIASES = 'aliases'

    # список фотоформатов, спионеренный в RawTherapee
    IMAGE_FILE_EXTENSIONS = {'.nef', '.cr2', '.cr3', '.tif', '.tiff', '.crf',
        '.crw', '.3fr', '.arw', '.dcr', '.dng', '.fff', '.iiq', '.kdc',
        '.mef', '.mos', '.mrw', '.nrw', '.orf', '.pef', '.raf', '.raw',
        '.rw2', '.rwl', '.rwz', '.sr2', '.srf', '.srw', '.x3f', '.arq'}
    # и видео, какое удалось вспомнить
    VIDEO_FILE_EXTENSIONS = {'.mov', '.avi', '.mpg', '.vob', '.ts',
        '.mp4', '.m4v', '.mkv'}

    E_BADVAL = 'Неправильное значение параметра "%s" в секции "%s" файла настроек "%s" - %s'
    E_BADVAL2 = 'Неправильное значение параметра "%s" в секции "%s" файла настроек "%s"'
    E_DUPVAL = 'Имя параметра "%s" использовано более одного раза в секции "%s" файла настроек "%s"'
    E_NOVAL = 'Отсутствует значение параметра "%s" в секции "%s" файла настроек "%s"'
    E_NOSECTION = 'В файле настроек "%s" отсутствует секция "%s"'
    E_CONFIG = 'Ошибка обработки файла настроек - %s'
    E_CMDLINE = 'параметр %d командной строки: %s'

    def setup_work_mode(self):
        """Вызывать после изменения workModeMove (напр. из GUI)"""

        if self.modeMoveFiles:
            self.modeMessages = workmodemsgs('переместить', 'перемещено')
            self.modeFileOp = shutil.move
        else:
            self.modeMessages = workmodemsgs('скопировать', 'скопировано')
            self.modeFileOp = shutil.copy

    def __init__(self, args):
        """Разбор командной строки, поиск и загрузка файла конфигурации.

        args            - аргументы командной строки (список строк),
                          например, значение sys.argv

        В первую очередь пытается определить режим работы
        (перемещение/копирование), и режим интерфейса (консоль/графика).

        В случае успеха self.error устанавливается в None.
        В случае ошибок присваивает self.error строку с сообщением об ошибке."""

        #
        # параметры
        #
        self.modeMoveFiles = None
        self.GUImode = False

        self.modeMessages = None
        self.modeFileOp = None

        # каталог, из которого копируются (или перемещаются) изображения
        self.sourceDirs = []

        # каталог, в который копируются (или перемещаются) изображения
        self.destinationDir = None

        # поддерживаемые типы файлов (по расширениям)
        self.knownImageTypes = self.IMAGE_FILE_EXTENSIONS
        self.knownVideoTypes = self.VIDEO_FILE_EXTENSIONS

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
        # см. далее except!
        #
        self.error = None

        try:
            # определение режима работы - делаем в самом начале,
            # т.к. нужно сразу знать, как именно показывать сообщения
            # об ошибках
            # __detect_work_mode() по возможности НЕ должно генерировать
            # исключений!
            self.__detect_work_mode(args)
            self.setup_work_mode()

            #
            # ищем файл конфигурации
            #
            self.configPath = self.__get_config_path(args[0])
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
            # ...а вот теперь - разгребаем командную строку, т.к. ее параметры
            # перекрывают файл настроек
            #

            self.__parse_cmdline_options(args)

        except self.Error as ex:
            # конструктор НЕ ДОЛЖЕН падать от self.Error - оно будет
            # обработано снаружи по содержимому self.error
            # с прочими исключениями - падаем, ибо это предположительно
            # что-то более серьёзное
            # на этом этапе поля self.modeMoveFiles,
            # self.GUImode уже установлены в известные значения
            # и сообщение об ошибке где-то снаружи должно быть показано
            # в правильном режиме
            self.error = repr(ex)

    CMDOPT_GUI = {'-g', '--gui'}
    CMDOPT_NOGUI = {'-n', '--no-gui'}
    CMDOPT_COPY = {'-c', '--copy'}
    CMDOPT_MOVE = {'-m', '--move'}
    CMDOPTS_WORKMODE = CMDOPT_COPY | CMDOPT_MOVE | CMDOPT_GUI | CMDOPT_NOGUI
    __CMDOPT_IF_EXISTS_SHORT = '-e'
    CMDOPT_IF_EXISTS = {__CMDOPT_IF_EXISTS_SHORT, '--if-exists'}

    def __detect_work_mode(self, args):
        """Определение режима работы (перемещение/копирование,
        консольный/графический) по имени исполняемого файла и/или
        по ключам командной строки."""

        #
        # определяем, кто мы такое
        #
        bname = os.path.basename(args[0])

        # имя того, что запущено, в т.ч. если вся куча засунута
        # в архив ZIP

        bnamecmd = os.path.splitext(bname)[0].lower()

        if bnamecmd in (Environment.MODE_MOVE, Environment.MODE_MOVE_GUI):
            self.modeMoveFiles = True
        elif bnamecmd in (Environment.MODE_COPY, Environment.MODE_COPY_GUI):
            self.modeMoveFiles = False
        else:
            # ругаться будем потом, если режим не указан в командной строке
            self.modeMoveFiles = None

        self.GUImode = bnamecmd in (Environment.MODE_MOVE_GUI, Environment.MODE_COPY_GUI)
        # а в непонятных случаях будем считать, что режим морды - консольный

        # предварительный и ограниченный разбор параметров командной строки
        # нужен для определения gui/nogui ДО создания экземпляра Environment,
        # чтобы знать, как отображать потом сообщения об ошибках
        # копирование/перемещение определяем тут же, раз уж именно здесь
        # определяли его по имени исполняемого файла
        for arg in args[1:]:
            if arg.startswith('-'):
                if arg in self.CMDOPT_GUI:
                    self.GUImode = True
                elif arg in self.CMDOPT_NOGUI:
                    self.GUImode = False
                elif arg in self.CMDOPT_MOVE:
                    self.modeMoveFiles = True
                elif arg in self.CMDOPT_COPY:
                    self.modeMoveFiles = False
                # на неизвестные опции ругаемся не здесь, а в __parse_cmdline_options()

        if self.modeMoveFiles is None:
            raise Environment.Error('Меня зовут %s, и я не знаю, что делать.' % bname)

    def __parse_cmdline_options(self, args):
        """Разбор аргументов командной строки"""

        carg = None

        for argnum, arg in enumerate(args[1:], 1):
            if carg:
                if carg in self.CMDOPT_IF_EXISTS:
                    if arg in self.FEXIST_OPTIONS:
                        self.ifFileExists = self.FEXIST_OPTIONS[arg]
                    else:
                        raise self.Error(self.E_CMDLINE % (argnum, 'недопустимое значение параметра "%s"' % carg))
                carg = None
            elif arg.startswith('-'):
                if arg in self.CMDOPTS_WORKMODE:
                    # режим междумордия и работы с файлами был определён ранее, вызовом __detect_work_mode()
                    pass
                elif arg in self.CMDOPT_IF_EXISTS:
                    carg = self.__CMDOPT_IF_EXISTS_SHORT
                else:
                    raise self.Error(self.E_CMDLINE % (argnum, 'параметр "%s" не поддерживается' % arg))
            else:
                raise self.Error(self.E_CMDLINE % (argnum, 'ненужное имя файла'))

        if carg:
            raise self.Error(self.E_CMDLINE % (argnum, 'не указано значение параметра "%s"' % carg))

    def __read_config_paths(self):
        """Разбор секции paths файла настроек"""

        #
        # каталоги с исходными файлами
        #

        rawSrcDirs = map(lambda s: s.strip(), self.cfg.getstr(self.SEC_PATHS, self.OPT_SRC_DIRS).split(':'))

        for ixsd, srcdir in enumerate(rawSrcDirs, 1):
            if srcdir:
                # пустые строки пропускаем - опухнешь на каждую мелочь ругаться

                srcdir = validate_path(srcdir)

                # путь добавляем во внутренний список, если он не совпадает
                # с каким-то из уже добавленных;
                # существование каталога будет проверено при обработке файлов

                if self.same_src_dir(srcdir):
                    raise self.Error(self.E_BADVAL % (self.OPT_SRC_DIRS, self.SEC_PATHS, self.configPath,
                        'путь %d (%s) совпадает с одним из уже указанных' % (ixsd, srcdir)))

                self.sourceDirs.append(srcdir)

        if not self.sourceDirs:
            raise self.Error(self.E_BADVAL % (self.OPT_SRC_DIRS, self.SEC_PATHS, self.configPath, 'не указано ни одного существующего исходного каталога'))

        #
        # каталог назначения
        #

        self.destinationDir = self.cfg.getstr(self.SEC_PATHS, self.OPT_DEST_DIR)

        if not self.destinationDir:
            raise self.Error(self.E_NOVAL % (self.OPT_DEST_DIR, self.SEC_PATHS, self.configPath))

        self.destinationDir = validate_path(self.destinationDir)

        if not os.path.exists(self.destinationDir):
            raise self.Error(self.E_BADVAL % (self.OPT_DEST_DIR, self.SEC_PATHS, self.configPath,
                'путь "%s" не существует' % self.destinationDir))

        if not os.path.isdir(self.destinationDir):
            raise self.Error(self.E_BADVAL % (self.OPT_DEST_DIR, self.SEC_PATHS, self.configPath,
                'путь "%s" указывает не на каталог' % self.destinationDir))

        if self.same_src_dir(self.destinationDir):
            raise self.Error(self.E_BADVAL % (self.OPT_DEST_DIR, self.SEC_PATHS, self.configPath,
                'каталог назначения совпадает с одним из исходных каталогов'))

    def same_src_dir(self, dirname):
        """Возвращает True, если каталог dirname совпадает с одним из
        каталогов списка self.sourceDirs."""

        for sd in self.sourceDirs:
            if same_dir(sd, dirname):
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
        def __get_ext_set_param(sec, opt):
            ret = set()

            kts = filter(None, self.cfg.getstr(sec, opt).lower().split(None))

            for ktype in kts:
                if not ktype.startswith('.'):
                    ktype = '.%s' % ktype

                ret.add(ktype)

            return ret

        self.knownImageTypes.update(__get_ext_set_param(self.SEC_OPTIONS, self.OPT_KNOWN_IMAGE_TYPES))
        self.knownVideoTypes.update(__get_ext_set_param(self.SEC_OPTIONS, self.OPT_KNOWN_VIDEO_TYPES))

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
        self.cfg.set(self.SEC_PATHS, self.OPT_SRC_DIRS, ':'.join(self.sourceDirs))
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

        if cameraModel:
            cameraModel = cameraModel.lower()

            if cameraModel in self.templates:
                return self.templates[cameraModel]

        return self.templates[self.DEFAULT_TEMPLATE_NAME]

    def known_file_type(self, filename):
        """Определяет по расширению имени filename, известен ли программе
        тип файла, а также подтип - изображение или видео.
        Возвращает значение FileMetadata.FILE_TYPE_*, если тип известен,
        иначе возвращает None."""

        ext = os.path.splitext(filename)[1].lower()

        if ext in self.knownImageTypes:
            return FileMetadata.FILE_TYPE_IMAGE
        elif ext in self.knownVideoTypes:
            return FileMetadata.FILE_TYPE_VIDEO
        else:
            return None

    def __str__(self):
        """Для отладки"""
        return '''cfg = %s
modeMoveFiles = %s
GUImode = %s
modeMessages = %s
modeFileOp = %s
sourceDirs = %s
destinationDir = "%s"
ifFileExists = %s
knownImageTypes = "%s"
knownVideoTypes = "%s"
showSrcDir = %s
aliases = %s
templates = %s''' % (self.cfg,
    self.modeMoveFiles, self.GUImode,
    self.modeMessages,
    self.modeFileOp,
    str(self.sourceDirs), self.destinationDir,
    self.FEXISTS_OPTIONS_STR[self.ifFileExists],
    str(self.knownImageTypes),
    str(self.knownVideoTypes),
    self.showSrcDir,
    self.aliases,
    ', '.join(map(str, self.templates.values())))


if __name__ == '__main__':
    print('[%s test]' % __file__)

    try:
        sys.argv[0] = 'photocpg.py'
        print(sys.argv)
        env = Environment(sys.argv)
        if env.error:
            raise Exception(env.error)
        #env.save()
    except Environment.Error as ex:
        print('** %s' % str(ex))
        exit(1)

    print(env)
    #tpl = env.get_template('')
    #print('template:', tpl, repr(tpl))

    print(env.known_file_type('filename.m4v'))
