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


TITLE = 'PhotoMV'
VERSION = '1.2.3'
TITLE_VERSION = '%s v%s\n' % (TITLE, VERSION)


import os, os.path
from traceback import format_exception
from sys import exc_info


def print_exception():
    """Печать текущего исключения"""

    for s in format_exception(*exc_info()):
        print(s)


def make_dirs(path, excpt=None):
    """Создание пути path с подкаталогами.

    В случае успеха возвращает None.
    В случае ошибки:
    - если параметр excpt - экземпляр класса Exception, то генерирует
      соотв. исключение;
    - иначе возвращает строку с сообщением об ошибке."""

    try:
        if not os.path.exists(path):
            os.makedirs(path)

        return None

    except OSError as ex:
        emsg = 'Не удалось создать каталог "%s": %s' % (path, ex)

        if isinstance(excpt, Exception):
            raise excpt(emsg)
        else:
            return emsg


def validate_path(path):
    return os.path.abspath(os.path.expanduser(path))


INVALID_FNAME_CHARS = ':\/<>'

def normalize_filename(s):
    """Ищет в строке символы, недопустимые для имени файла
    (без каталога) - разделители путей, двоеточия и т.п.
    Возвращает строку, где недопустимые символы заменены на "_"."""

    return ''.join(map(lambda c: '_' if c in INVALID_FNAME_CHARS else c, s))


def same_dir(dir1, dir2):
    """Возвращает True, если оба параметра указывают на один каталог,
    или один является подкаталогом другого.
    Для правильности проверки оба пути должны быть абсолютными."""

    dir1 = os.path.abspath(dir1)
    dir2 = os.path.abspath(dir2)

    if dir1 == dir2: #os.path.samefile(dir1, dir2):
        return True

    r = os.path.normpath(os.path.commonprefix((dir1, dir2)))
    return r == dir1 or r == dir2
    #return os.path.samefile(r, dir1) or os.path.samefile(r, dir2)


if __name__ == '__main__':
    print('[%s test]' % __file__)

    #print(normalize_filename('/some/filename:text'))
