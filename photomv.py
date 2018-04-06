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
from locale import getdefaultlocale

from pmvcommon import *
from pmvconfig import *


def process_files(env, ui, srcDirs=None):
    """Обработка исходных каталогов.

    env     - экземпляр pmvconfig.Environment
    ui      - экземпляр класса pmvui.UserInterface
    srcDirs - список исходных каталогов;
              если None или пустой список - будет использован
              список env.sourceDirs

    Возвращает список строк, содержащих сообщения
    (кол-во обработанных файлов и т.п.)."""

    statTotalFiles = 0
    statProcessedFiles = 0
    statSkippedFiles = 0

    #
    # 1й проход - подсчет общего количества файлов
    #
    ui.job_progress(0.0, 'Подготовка...')

    if not srcDirs:
        srcDirs = env.sourceDirs

    # с этим списком будет работать 2й проход
    # содержит он кортежи вида ('каталог', [список файлов]),
    # где список файлов - список строк с именами файлов;
    # да, оно память жрёть, но не гигабайты же
    # а кто натравит photomv на гигантскую файлопомойку -
    # сам себе злой буратино
    sourcedirs = []

    for srcdir in srcDirs:
        if not os.path.exists(srcdir) or not os.path.isdir(srcdir):
            ui.job_error('путь "%s" не существует или указывает не на каталог' % srcdir)
        else:
            for srcroot, dirs, files in os.walk(srcdir):
                ui.job_progress(-1.0) # progressbar.pulse()
                flist = [] # список файлов допустимых типов из текущего каталога

                for fname in files:
                    # файлы неизвестных типов отсеиваем заранее
                    ftype = env.knownFileTypes.get_file_type_by_name(fname)
                    if ftype is None:
                        continue

                    flist.append(fname)

                nfiles = len(flist)
                if nfiles:
                    sourcedirs.append((srcroot, flist))
                    statTotalFiles += nfiles

    if statTotalFiles == 0:
        return ['не с чем работать - нет файлов']

    #
    # 2й проход - собственно обработка файлов
    #
    if statTotalFiles:
        nFileIx = 0

        for srcdir, flist in sourcedirs:
            ui.job_show_dir(srcdir)

            for fname in flist:
                nFileIx += 1

                srcPathName = os.path.join(srcdir, fname)
                if os.path.isfile(srcPathName):
                    # всякие там символические ссылки пока нафиг
                    try:
                        metadata = FileMetadata(srcPathName, env.knownFileTypes)
                    except Exception as ex:
                        statSkippedFiles += 1

                        ui.job_error('файл "%s" повреждён или ошибка чтения (%s)' % (fname, str(ex)))
                        # с кривыми файлами ничего не делаем
                        continue

                    #
                    # выясняем, каким шаблоном создавать новое имя файла
                    #

                    fntemplate = env.get_template(metadata.fields[metadata.MODEL])

                    newSubDir, newFileName, newFileExt = fntemplate.get_new_file_name(env, metadata)

                    destPath = os.path.join(env.destinationDir, newSubDir)
                    make_dirs(destPath, OSError)

                    newFileNameExt = newFileName + newFileExt

                    ui.job_progress(float(nFileIx) / statTotalFiles, '%s -> %s' % (fname, newFileNameExt))

                    destPathName = os.path.join(destPath, newFileNameExt)

                    if os.path.exists(destPathName):
                        if env.ifFileExists == env.FEXIST_SKIP:
                            ui.job_warning('файл "%s" уже существует, пропускаю' % newFileNameExt)
                            statSkippedFiles += 1
                            continue
                        elif env.ifFileExists == env.FEXIST_RENAME:
                            # пытаемся подобрать незанятое имя

                            canBeRenamed = False

                            # нефиг больше 10 повторов... и 10-то много
                            for unum in range(1, 11):
                                destPathName = os.path.join(destPath, '%s-%d%s' % (newFileName, unum, newFileExt))

                                if not os.path.exists(destPathName):
                                    canBeRenamed = True
                                    break

                            if not canBeRenamed:
                                ui.job_error('в каталоге "%s" слишком много файлов с именем %s*%s' % (destPath, newFileName, newFileExt))

                                statSkippedFiles += 1
                                continue

                        # else:
                        # env.FEXIST_OVERWRITE - перезаписываем

                    #
                    # а вот теперь копируем или перемещаем файл
                    #

                    try:
                        env.modeFileOp(srcPathName, destPathName)
                        statProcessedFiles += 1
                    except (IOError, os.error) as emsg:
                        print_exception()
                        skippedFiles += 1
                        ui.job_error(u'не удалось % файл - %s' % (env.modeMessages.errmsg, repr(emsg)))

    return ('Всего файлов: %d\n%s: %d\nпропущено: %d' % (statTotalFiles,
        env.modeMessages.statmsg, statProcessedFiles,
        statSkippedFiles),)


def main(args):
    ui = None
    try:
        env = Environment(args)

        if env.GUImode:
            from pmvgtkui import GTKUI as UIClass
        else:
            from pmvtermui import TerminalUI as UIClass

        if env.error:
            # см. Environment.__init__()
            # ругаемся только сейчас, когда уже известен UIClass
            raise Exception(env.error)

        ui = UIClass(env, process_files)
        ui.run()

    except Exception as ex:
        print_exception()
        UIClass.show_fatal_error(repr(ex))

        return 1


    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
