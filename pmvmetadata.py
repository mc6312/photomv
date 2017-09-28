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


class FileMetadata():
    """Метаданные изображения или видеофайла.

    Содержит только поля, поддерживаемые FileNameTemplate."""

    __EXIF_DT_TAGS = ['Exif.Image.OriginalDateTime', 'Exif.Image.DateTime']
    __EXIF_MODEL = 'Exif.Image.Model'

    FILE_TYPE_IMAGE, FILE_TYPE_VIDEO = range(2)

    __IMAGE_FTYPES = {'.jpg', '.jpeg', '.tif', '.tiff',
        '.nef', '.'}

    __N_FIELDS = 10

    MDF_TYPE, MDF_MODEL, MDF_ALIAS, MDF_PREFIX, MDF_NUMBER, \
    MDF_YEAR, MDF_MONTH, MDF_DAY, MDF_HOUR, MDF_MINUTE = range(__N_FIELDS)

    def __init__(self, filename):
        """Извлечение метаданных из файла filename.

        fields - поля с метаданными (см. константы MDF_xxx)

        В случае неизвестного типа файлов всем полям присваивается
        значение None.
        В случае прочих ошибок генерируются исключения."""

        self.fields = [None] * self.__N_FIELDS

        fname, fext = os.path.splitext(filename)

        try:
            md = GExiv2.Metadata(filename)

        except GLib.Error as emsg:
            # не открылось ваще, или не изображение.
            # подробности мну в данный момент не колышут.
            md = None
            print(u'Warning: can nog get metadata from file "%s"' % filename)

            if md:
                # пытаемся выковырять нужный тэг
                for tagname in self.__EXIF_DT_TAGS:
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
            return datetime.datetime.fromtimestamp(os.stat(filename).st_mtime)


            return (None, None)
        except Exception as ex:
            return (None, str(ex))



def get_image_timestamp(imgfilename):
    """Получение даты создания изображения.

    При наличии соотв. тэга EXIF - данные берутся из него,
    иначе берется время создания файла.
    Дата возвращается в виде datetime.datetime.
    Если файл не является изображением (с т.з. потрохов exiv2),
    то функция возвращает None.

    Получение метаданных сделано для pyexiv2/gexiv v0.1.x
    (т.к. оно на момент написания было в пузиториях убунты),
    м.б. несовместимо с текущей версией 0.3.х"""



if __name__ == '__main__':
    print('[%s test]' % __file__)

    ftype, r = FileMetadata.get_file_metadata(os.path.expanduser('~/downloads/src/DSCN_0464.NEF'))

    if ftype is None:
        if r is None:
            print('Unknown file type')
        else:
            print('Can not get file metadata, %s' % r)
    else:
        print(str(r))
