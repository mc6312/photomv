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



import sys
import os, os.path
import datetime
import shutil
from locale import getdefaultlocale

from pmvcommon import *
from pmvconfig import *


'''



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
