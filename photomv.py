#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Copyright 2017 MC-6312

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>."""


from gi import require_version as gi_require_version
gi_require_version('GExiv2', '0.10')
from gi.repository import GExiv2

import sys
import os, os.path
import datetime
import shutil
from locale import getdefaultlocale

from pmvcommon import *
from pmvconfig import *


'''

#
# настройки
#


# имя дополнительного подкаталога в каталоге назначения
# если пустая строка - подкаталог не создается
cfg_subdir = u''

# имя подкаталога для видеофайлов
cfg_subdir_video = u''

#
#
#

# Загрузка настроек.
# Если файл <homedir>/.photocp.ini существует, то из него загружаются
# настройки. Для параметров, не указанных в файле, задаются значения
# по умолчанию.



# асспейсибо гнидоопоссуму за кривую поддержку юникода во всем пыхтоне
fenc = getdefaultlocale()[1]
if not fenc:
    fenc = sys.getfilesystemencoding()


fnconfig = os.path.expanduser(u'~/.photocp.ini')
if os.path.exists(fnconfig):
    if not os.path.isfile(fnconfig):
        print(u'%s is not a file' % fnconfig)
        exit(2)

    cfg = ConfigParser()
    cfg.read(fnconfig)

    E_BADVAL = u'Invalid value of option "%s" in section "%s" of file "%s"'
    #
    # пути
    #

    SEC_PATHS = u'paths'

    def cfg_getstr(secname, varname):
        if cfg.has_option(secname, varname):
            return cfg.get(secname, varname).strip()
        else:
            return u''

    def cfg_getpath(varname):
        if cfg.has_option(SEC_PATHS, varname):
            v = cfg_getstr(SEC_PATHS, varname)
            if v:
                return validate_path(v)
            else:
                return None
        else:
            return None

    cfg_source_dir = cfg_getpath(u'sourcedir')
    cfg_destination_dir = cfg_getpath(u'destdir')

    OPT_SUBDIR = u'subdir'
    cfg_subdir = cfg_getstr(SEC_PATHS, OPT_SUBDIR)
    if cfg_subdir.find(os.path.sep) >= 0:
        print(E_BADVAL % (OPT_SUBDIR, SEC_PATHS, fnconfig))

    OPT_SUBDIR_VIDEO = u'subdir_video'
    cfg_subdir_video = cfg_getstr(SEC_PATHS, OPT_SUBDIR_VIDEO)
    if cfg_subdir_video.find(os.path.sep) >= 0:
        print(E_BADVAL % (OPT_SUBDIR_VIDEO, SEC_PATHS, fnconfig))

    #
    # настройки
    #
    SEC_OPTIONS = u'options'
    if cfg.has_option(SEC_OPTIONS, OPT_IF_EXISTS):
        s = cfg.get(SEC_OPTIONS, OPT_IF_EXISTS).lower()
        if s in fexist_options:
            cfg_if_file_exists = fexist_options[s]
        else:
            print(E_BADVAL % (OPT_IF_EXISTS, SEC_OPTIONS, fnconfig))
            exit(1)
else:
    print(u'Config file (%s) is not found, creating default' % fnconfig)

    try:
        fo = open(fnconfig, 'w+', encoding=fenc)
        try:
            fo.write("""[paths]
sourcedir =
destdir =
subdir =
subdir_video =

[options]
; s[kip], r[ename] or o[verwrite]
if-exists = rename""")
        finally:
            fo.close()
        exit(1)
    except (IOError, os.error) as emsg:
        print(u'Can not create file "%s", %s' % (fnconfig, emsg))
        exit(1)

# проверка командной строки
# если в ней есть пути - они заменяют то, что загружено из конфига

# проверяем настройки

def check_is_dir(path, what):
    if path:
        path = path.strip()

    if not path:
        print(u'%s directory not specified. Check settings in "%s"' % (what, fnconfig))
        exit(1)

    if os.path.exists(path):
        if not os.path.isdir(path):
            print(u'%s directory path (%s) points to file' % (what, path))
            exit(1)

        ret = True
    else:
        ret = False

    return (path, ret)

# каталог-источник. должен существовать
cfg_sd = check_is_dir(cfg_source_dir, u'Source')
if not cfg_sd[1]:
    print(u'Source directory (%s) is not exist' % cfg_sd[0])
    exit(1)
else:
    cfg_source_dir = cfg_sd[0]

def make_dirs(path):
    try:
        os.makedirs(path)
    except os.error as emsg:
        print(u'Can not create directory "%s", %s' % (path, emsg))
        exit(2)

# каталог-приемник. при необходимости создаем
cfg_dd = check_is_dir(cfg_destination_dir, u'Destination')
cfg_destination_dir = cfg_dd[0]
if not cfg_dd[1]:
    make_dirs(cfg_destination_dir)

    if cfg_source_dir == cfg_destination_dir:
        print(u'Source and destination directories can not be same')
        exit(1)


# проверяем имя скрипта, и выбираем соотв. режим работы
myname = sys.argv[0]
if myname:
    myname = os.path.splitext(os.path.split(myname)[1])[0].strip().lower()

if myname == u'photomv':
    work_mode = (u'Moving', shutil.move)
else:
    work_mode = (u'Copying', shutil.copy)

EXIF_DT_TAGS = ['Exif.Image.OriginalDateTime', 'Exif.Image.DateTime']

#VIDEO_FTYPES = moo # дабы интерпретатор ругался на недоделанный скрипт

def get_image_timestamp(imgfilename):
    """Получение даты создания изображения.

    При наличии соотв. тэга EXIF - данные берутся из него,
    иначе берется время создания файла.
    Дата возвращается в виде datetime.datetime.
    Если файл не является изображением (с т.з. потрохов exiv2),
    то функция возвращает None.

    Сделано для pyexiv2 v0.1.x (т.к. оно на момент написания было
    в пузиториях убунты), м.б. несовместимо с текущей версией 0.3.х"""

    dt = None

    try:
        md = GExiv2.Metadata(imgfilename)

    except Exception as emsg:
        # не открылось ваще, или не изображение.
        # подробности мну в данный момент не колышут.
        md = None
        print(u'Warning: can nog get metadata from file "%s"' % imgfilename)

    if md:
        # пытаемся выковырять нужный тэг
        for tagname in EXIF_DT_TAGS:
            if tagname in md:
                # 2016:07:11 20:28:50
                dts = md[tagname]
                try:
                    dt = datetime.datetime.strptime(u'%Y:%m:%d %H:%M:%s')
                except:
                    dt = None
                    continue
                break

    if dt:
        # вахЪ! есть нужный тэг
        dt = dt.value
        if dt.year > 1800 and dt.month >=1 and dt.month <= 12 and dt.day >=1 and dt.day <= 31:
            # ...и даже содержит че-то похожее на осмысленное
            return dt

    # абломинго. возвращаем дату создания файла...
    # точнее, дату последней модификации, т.к. os.stat().st_ctime
    # ведет себя по разному на разных платформах
    return datetime.datetime.fromtimestamp(os.stat(imgfilename).st_mtime)

#
# поперли чавкать файлами
#

def main(argv):
    disp_dest = None

    for roots, dirs, files in os.walk(cfg_source_dir):
        for fname in files:
            fpath = os.path.join(roots, fname)
            if os.path.isfile(fpath):
                dt = get_image_timestamp(fpath)

                if dt:
                    fnext = os.path.splitext(fname)

                    fdestdir = os.path.join(cfg_destination_dir,
                                            u'%.4d' % dt.year,
                                            u'%.2d' % dt.month,
                                            u'%.2d' % dt.day)

                    if cfg_subdir:
                        fdestdir = os.path.join(fdestdir, cfg_subdir)

                    if disp_dest != fdestdir:
                        disp_dest = fdestdir
                        print(u'%s images to %s' % (work_mode[0], disp_dest))
                        if not os.path.isdir(fdestdir):
                            make_dirs(fdestdir)

                    fnewname = u'p%.4d%.2d%.2d_%s' % (dt.year, dt.month, dt.day,
                                                      u''.join(filter(lambda c: c.isdigit(), fnext[0])))
                    fnewext = fnext[1].lower()
                    fnewpathname = os.path.join(fdestdir, fnewname)

                    # чо делаем с уже существующим файлом?
                    fnewpath = fnewpathname + fnewext
                    fnsuffix = u''

                    if os.path.exists(fnewpath):
                        if cfg_if_file_exists == FEXIST_SKIP:
                            continue
                        elif cfg_if_file_exists == FEXIST_RENAME:
                            fnuniq = False
                            nsuffix = 0
                            while nsuffix < 99:
                                nsuffix += 1
                                fnsuffix = u'-%.2d' % nsuffix
                                fnewpath = fnewpathname + fnsuffix + fnewext
                                if not os.path.exists(fnewpath):
                                    fnuniq = True
                                    break

                            if not fnuniq:
                                print(u'Too many similar file names in this directory')
                                exit(2)

                    print(u'%s -> %s' % (fname, fnewname + fnsuffix + fnewext))
                    try:
                        work_mode[1](fpath, fnewpath)
                    except (IOError, os.error) as emsg:
                        print(u'  error %s' % emsg)
                else:
                    print(u'%s is not an image file or cannot be opened' % fname)
'''

def main(args):
    print('%s v%s\n' % (TITLE, VERSION))

    try:
        env = Environment(args)
    except Environment.Error as ex:
        print(str(ex))
        return 1


    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
