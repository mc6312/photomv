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


from pmvmetadata import FileMetadata
import os.path


class FileNameTemplate():
    """Шаблон для переименования файлов"""

    # поля шаблона
    YEAR, MONTH, DAY, HOUR, MINUTE, \
    MODEL, ALIAS, PREFIX, NUMBER, FILETYPE, LONGFILETYPE, \
    FILENAME = range(12)

    __FILETYPE_STR = {FileMetadata.FILE_TYPE_IMAGE:'p',
        FileMetadata.FILE_TYPE_RAW_IMAGE:'p', # для совместимости
        FileMetadata.FILE_TYPE_VIDEO:'v'}

    __LONG_FILETYPE_STR = {FileMetadata.FILE_TYPE_IMAGE:'photo',
        FileMetadata.FILE_TYPE_RAW_IMAGE:'raw',
        FileMetadata.FILE_TYPE_VIDEO:'video'}

    # отображение полей экземпляра FileMetadata в поля FileNameTemplate
    # для полей FileNameTemplate.ALIAS, .FILETYPE и .FILENAME - будет спец. обработка
    __METADATA_FIELDS = {YEAR:FileMetadata.YEAR, MONTH:FileMetadata.MONTH,
        DAY:FileMetadata.DAY, HOUR:FileMetadata.HOUR, MINUTE:FileMetadata.MINUTE,
        MODEL:FileMetadata.MODEL,
        PREFIX:FileMetadata.PREFIX, NUMBER:FileMetadata.NUMBER}

    FLD_NAMES = {'y':YEAR, 'year':YEAR,     # год (в виде четырёхзначного числа)
        'mon':MONTH, 'month':MONTH,         # месяц - двухзначный, день и т.п. - тоже
        'd':DAY, 'day':DAY,                 # день
        'h':HOUR, 'hour':HOUR,              # час
        'm':MINUTE, 'minute':MINUTE,        # минута
        'model':MODEL,                      # модель камеры
        'a':ALIAS, 'alias':ALIAS,           # сокращенное название модели (если есть в Environment.aliases)
        'p':PREFIX, 'prefix':PREFIX,        # префикс из оригинального имени файла
        'n':NUMBER, 'number':NUMBER,        # номер снимка из оригинального имени файла или EXIF
        't':FILETYPE, 'type':FILETYPE,      # тип файла, односимвольный вариант
        'l':LONGFILETYPE, 'longtype':LONGFILETYPE, # тип файла, длинный вариант
        'f':FILENAME, 'filename':FILENAME}  # оригинальное имя файла (без расширения)

    class Error(Exception):
        pass

    ERROR = 'ошибка в позиции %d шаблона - %s'

    def __init__(self, tplstr):
        """Разбор строки s с шаблоном имени файла"""

        self.fields = []
        # список может содержать строки и целые числа
        # строки помещаются в новое имя файла как есть,
        # целые числа (константы FileMetadata.xxx) заменяются соответствующими
        # полями метаданных

        tpllen = len(tplstr)
        tplend = tpllen - 1

        tplix = 0

        # принудительная чистка
        while tplix < tplend and tplstr[tplix] in '/\\': tplix += 1

        if tplix > tplend:
            raise self.Error(self.ERROR % (tplix, 'пустой шаблон'))

        tstop = '{'
        tplstart = tplix
        tbracket = False
        c = None

        def flush_word(tbracket, tword):
            if tbracket:
                # проверяем макрос
                tword = tword.strip()
                if not tword:
                    raise self.Error(self.ERROR % (tplix, 'пустое имя макроса'))

                tword = tword.lower()

                if tword not in self.FLD_NAMES:
                    raise self.Error(self.ERROR % (tplix, 'недопустимое имя макроса - "%s"' % tword))
                else:
                    # добавляем макрос
                    self.fields.append(self.FLD_NAMES[tword])
            else:
                # добавляем простой текст
                if tword:
                    self.fields.append(tword)

        while tplix <= tplend:
            while tplix <= tplend:
                c = tplstr[tplix]

                if c in '{}':
                    if tplix < tplend:
                        if tplstr[tplix+1] == c:
                            tplix += 2
                            continue

                    if c != tstop:
                        raise self.Error(self.ERROR % (tplix, 'недопустимое появление "%s"' % c))

                    if c == '}':
                        tbracket = True

                    tstop = '}' if tstop == '{' else '{'
                    break

                tplix += 1

            if tplix >= tplend:
                break

            flush_word(tbracket, tplstr[tplstart:tplix])
            if tbracket:
                tbracket = False

            tplix += 1
            tplstart = tplix

        if tplstart < tplend:
            if tstop == '}':
                raise self.Error(self.ERROR % (tplix, 'незавершённый макрос'))
            else:
                flush_word(tbracket, tplstr[tplstart:tplix])

    def get_field_str(self, env, metadata, fldix):
        """Возвращает поле шаблона в виде строки.

        env         - экземпляр pmvconfig.Environment;
        metadata    - экземпляр pmvmetadata.FileMetadata;
        fldix       - номер поля (см. константы в начале класса);

        возвращает строку со значением поля, если поле имеется
        в метаданных, иначе возвращает символ "_"."""

        fv = None

        if fldix in self.__METADATA_FIELDS:
            fv = metadata.fields[self.__METADATA_FIELDS[fldix]]
        elif fldix == self.ALIAS:
            if metadata.fields[FileMetadata.MODEL]:
                model = metadata.fields[FileMetadata.MODEL].lower()

                if model in env.aliases:
                    fv = env.aliases[model]
        elif fldix == self.FILENAME:
            fv = metadata.fileName
        elif fldix == self.FILETYPE:
            nfx = metadata.fields[FileMetadata.FILETYPE]
            fv = self.__FILETYPE_STR[nfx] if nfx in self.__FILETYPE_STR else None
        elif fldix == self.LONGFILETYPE:
            nfx = metadata.fields[FileMetadata.FILETYPE]
            fv = self.__LONG_FILETYPE_STR[nfx] if nfx in self.__LONG_FILETYPE_STR else None

        return '_' if not fv else fv

    def get_new_file_name(self, env, metadata):
        """Создаёт имя файла на основе шаблона и метаданных файла.

        env         - экземпляр pmvconfig.Environment
        metadata    - экземпляр pmvmetadata.FileMetadata

        Возвращает кортеж из трёх элементов:
        1. относительный путь (если шаблон содержал разделители каталогов),
           или пустая строка;
        2. имя файла без расширения;
        3. расширение."""

        r = []
        for fld in self.fields:
            if isinstance(fld, str):
                # простой текст в шаблоне
                r.append(fld)
            else:
                r.append(self.get_field_str(env, metadata, fld))

        rawpath = os.path.split(''.join(r))
        return (*rawpath, metadata.fileExt)

    def __str__(self):
        """Для отладки"""

        return ''.join(map(lambda f: f if isinstance(f, str) else '<%d>' % f, self.fields))


defaultFileNameTemplate = FileNameTemplate('{filename}')


if __name__ == '__main__':
    print('[%s test]' % __file__)

    import sys
    from pmvconfig import Environment
    env = Environment(sys.argv)

    testFiles = (('~/downloads/src/p20170705_666.nef', FileMetadata.FILE_TYPE_RAW_IMAGE),
        ('~/downloads/src/v20150523_20150523-2.mkv', FileMetadata.FILE_TYPE_VIDEO))

    for fname, ftype in testFiles:
        metadata = FileMetadata(os.path.expanduser(fname), ftype)

        template = FileNameTemplate('{year}/{month}/{day}/{longtype}/{type}{year}{month}{day}_{ hour}{M}_{n}_{alias}_{f}')
        d, n, e = template.get_new_file_name(env, metadata)
        print(os.path.join('/home', d, n+e))
