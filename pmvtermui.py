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
from pmvui import *
import sys



class TerminalUI(UserInterface):
    def __init__(self, env, worker):
        super().__init__(env, worker)

        print(TITLE_VERSION)

        self.printIndent = '  ' if env.showSrcDir else ''

    def run(self):
        self.worker(self.env, self)

    def job_show_dir(self, dirname=''):
        if self.env.showSrcDir and dirname:
            print(dirname)

    def job_progress(self, progress, msg=''):
        if msg:
            print('%s%s' % (self.printIndent, msg))

    def job_error(self, msg):
        print('%s* %s' % (self.printIndent, msg))

    def job_warning(self, msg):
        self.job_error(msg)

    def critical_error(self, msg):
        print('* %s' % msg)

    @staticmethod
    def show_fatal_error(msg):
        print('* %s' % msg)


if __name__ == '__main__':
    print('[%s test]' % __file__)

    env = Environment(sys.argv)
    ui = TerminalUI(env, lambda e,ui: [])
