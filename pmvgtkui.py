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


from pmvcommon import *
from pmvconfig import *


# заглушка!
from pmvtermui import TerminalUI


class GTKUI(TerminalUI):
    def __init__(self, env):
        """Инициализация междумордия.
        env - экземпляр pmvconfig.Environment."""

        super().__init__()

        print('* Внимание! Графический интерфейс еще не сделан. Пырься в консоль.\n')


if __name__ == '__main__':
    print('[%s test]' % __file__)
