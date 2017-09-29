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


from gi import require_version as gi_require_version
gi_require_version('GExiv2', '0.10')
from gi.repository import GExiv2, GLib

import os, os.path
import datetime
from collections import namedtuple
import re


class FileMetadata():
    """Метаданные изображения или видеофайла.

    Содержит только поля, поддерживаемые FileNameTemplate."""

    __EXIF_DT_TAGS = ['Exif.Image.OriginalDateTime', 'Exif.Image.DateTime']
    __EXIF_MODEL = 'Exif.Image.Model'

    FILE_TYPE_IMAGE, FILE_TYPE_VIDEO = range(2)

    # файлы изображений; возможно, когда-нибудь придётся прикрутить
    # внешний файл с типами
    __IMAGE_FTYPES = {'.jpg', '.jpeg', '.tif', '.tiff', '.png',
        '.nef', '.crw', '.cr2', '.raf', '.pef', '.dng', '.arw', '.sr2',
        '.mrw', '.orf', '.kdc', '.rwz', '.rw2', '.mef'}

    # файлы видео (какие удалось вспомнить)
    __VIDEO_FTYPES = {'.avi', '.mov', '.mp4', '.m4v',
        '.ts', # некоторые камеры создают структуру каталогов с файлами а-ля блюрей
        '.mkv'}

    __N_FIELDS = 9

    FILETYPE, MODEL, PREFIX, NUMBER, \
    YEAR, MONTH, DAY, HOUR, MINUTE = range(__N_FIELDS)

    # выражение для выделения префикса и номера из имени файла
    # может не работать на файлах от некоторых камер - производители
    # с именами изгаляются как могут
    __rxFNameParts = re.compile(r'^_*([^\d_]*)_*(\d+)?', re.UNICODE)

    def __init__(self, filename):
        """Извлечение метаданных из файла filename.

        fields      - поля с метаданными (см. константы xxx)
                      содержат значения в виде строк или None
        fileName    - имя файла без расширения
        fileExt     - и расширение

        В случае неизвестного типа файлов всем полям присваивается
        значение None.
        В случае прочих ошибок генерируются исключения."""

        self.fields = [None] * self.__N_FIELDS

        self.fileName, self.fileExt = os.path.splitext(os.path.split(filename)[1])

        # при копировании или перемещении в новом имени файла расширение
        # в любом случае будет в нижнем регистре, ибо ваистену
        self.fileExt = self.fileExt.lower()

        if self.fileExt in self.__IMAGE_FTYPES:
            self.fields[self.FILETYPE] = self.FILE_TYPE_IMAGE
        elif self.fileExt in self.__VIDEO_FTYPES:
            self.fields[self.FILETYPE] = self.FILE_TYPE_VIDEO
        else:
            # иначе считаем, что файл неизвестного типа, и больше
            # ничего с ним не делаем
            return

        #
        # поля PREFIX, NUMBER
        #
        rm = self.__rxFNameParts.match(self.fileName)
        if rm:
            rmg = rm.groups()

            if rmg[0]:
                s = rmg[0].strip()
                if s:
                    self.fields[self.PREFIX] = s;

            self.fields[self.NUMBER] = rmg[1] # м.б. None

        #
        # Получение метаданных из EXIF
        # сделано для pyexiv2/gexiv v0.1.x
        # (т.к. оно на момент написания было в пузиториях убунты),
        # м.б. несовместимо с более поздними версиями?
        #

        md = None
        if self.fields[self.FILETYPE] == self.FILE_TYPE_IMAGE:
            # пытаемся выковыривать exif только из изображений
            # если видеофайлы и могут его содержать, один фиг exiv2
            # на обычных видеофайлах спотыкается

            md = GExiv2.Metadata(filename)

            # except GLib.Error as ex:
            # исключения тут обрабатывать не будем - пусть вылетают
            # потому как на правильных файлах известных типов оне вылетать не должны,
            # даже если в файле нет EXIF
            #    print('GLib.Error: %s - %s' % (GLib.strerror(ex.code), ex.message))

        dt = None

        if md:
            # ковыряемся в тэгах:

            #
            # сначала дату
            #
            for tagname in self.__EXIF_DT_TAGS:
                if tagname in md:
                    # 2016:07:11 20:28:50
                    dts = md[tagname]
                    try:
                        dt = datetime.datetime.strptime(dts, u'%Y:%m:%d %H:%M:%S')
                    except Exception as ex:
                        print('* Warning!', str(ex))
                        dt = None
                        continue
                    break

            #
            # MODEL
            #
            if self.__EXIF_MODEL in md:
                model = md[self.__EXIF_MODEL].strip()
                if model:
                    self.fields[self.MODEL] = model

        #
        # доковыриваем дату
        #
        if dt:
            # вахЪ! дата нашлась в EXIF!
            if dt.year < 1800 or dt.month <1 or dt.month > 12 or dt.day <1 or dt.day > 31:
                # но содержит какую-то херню
                dt = None
        else:
            # фигвам. берём в качестве даты создания mtime файла
            dt = datetime.datetime.fromtimestamp(os.stat(filename).st_mtime)

        self.fields[self.YEAR]      = '%.4d' % dt.year
        self.fields[self.MONTH]     = '%.2d' % dt.month
        self.fields[self.DAY]       = '%.2d' % dt.day
        self.fields[self.HOUR]      = '%.2d' % dt.hour
        self.fields[self.MINUTE]    = '%.2d' % dt.minute

    __FLD_NAMES = ('FILETYPE', 'MODEL', 'PREFIX', 'NUMBER',
        'YEAR', 'MONTH', 'DAY', 'HOUR', 'MINUTE')

    def __str__(self):
        """Для отладки"""

        r = ['fileName="%s"' % self.fileName, 'fileExt="%s"' % self.fileExt]
        r += (map(lambda f: '%s="%s"' % (self.__FLD_NAMES[f[0]], f[1]), enumerate(self.fields)))
        return '\n'.join(r)


if __name__ == '__main__':
    print('[%s test]' % __file__)

    testFile = '~/downloads/src/DSCN_0464.NEF'
    #testFile = '~/photos.current/2017/09/24/raw/p20170924_0690.nef'
    #testFile = '/pub/archive/photos/2007/01/01/DSC_2183.NEF'
    #testFile = '/pub/archive/photos/2004/05/22/05220027.jpg'

    try:
        r = FileMetadata(os.path.expanduser(testFile))
        print(r)
    except Exception as ex:
        print('Can not get file metadata, %s' % str(ex))
