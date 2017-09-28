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


class FileNameTemplate():
    """Шаблон для переименования файлов"""

    F_TYPE, F_MODEL, F_ALIAS, F_PREFIX, F_NUMBER,\
    F_YEAR, F_MONTH, F_DAY, F_HOUR, F_MINUTE = range(10)

    FLD_NAMES = {'y':F_YEAR, 'year':F_YEAR,
        'mon':F_MONTH, 'month':F_MONTH,
        'd':F_DAY, 'day':F_DAY,
        'h':F_HOUR, 'hour':F_HOUR,
        'm':F_MINUTE, 'minute':F_MINUTE,
        'model':F_MODEL,
        'a':F_ALIAS, 'alias':F_ALIAS,
        'p':F_PREFIX, 'prefix':F_PREFIX,
        'n':F_NUMBER, 'number':F_NUMBER,
        't':F_TYPE, 'type':F_TYPE}

    class Error(Exception):
        pass

    ERROR = 'ошибка в позиции %d шаблона - %s'

    def __init__(self, tplstr):
        """Разбор строки s с шаблоном имени файла"""

        self.fields = []
        # список может содержать строки и целые числа
        # строки помещаются в новое имя файла как есть,
        # целые числа (константы F_xxx) заменяются соответствующими
        # полями метаданных

        tpllen = len(tplstr)
        tplend = tpllen - 1

        tplix = 0
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

    def __str__(self):
        """Для отладки"""

        return ''.join(map(lambda f: f if isinstance(f, str) else '<%d>' % f, self.fields))


defaultFileNameTemplate = FileNameTemplate('{year}/{month}/{day}/{type}{year}{month}{day}_{hour}{minute}')


if __name__ == '__main__':
    print('[%s test]' % __file__)

    template = FileNameTemplate('{{boo}}{year}/{month}/{day}/{type}{year}{month}{day}_{ hour}{M}{{ moo }}')
    print(template)
