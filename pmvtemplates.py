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


class FileNameTemplate():
    """Шаблон для переименования файлов"""

    F_YEAR, F_MONTH, F_DAY, F_HOUR, F_MINUTE,\
    F_MODEL, F_ALIAS, F_PREFIX, F_NUMBER, F_TYPE = range(10)

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

        raise NotImplementedError('доделай меня')

        while tplix <= tplend:
            tplstart = tplix
            while tplix <= tplend and tplstr[tplix] != tstop:
                tplix += 1

            i
            tword = tplstr[tplstart:tplix]
            print('word:', tword)

            c = tplstr[tplix]
            tplix += 1

            #        raise self.Error(self.ERROR % (tplix, 'имя макроса не должно содержать "{"'))



if __name__ == '__main__':
    print('[%s test]' % __file__)

    template = FileNameTemplate('{year}/{{month}/{day}/{type}{year}{month}{day}_{}{')
