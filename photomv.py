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



def process_source_dir(env, ui, srcdir):
    """Обработка исходного каталога.

    env     - экземпляр pmvconfig.Environment
    ui      - экземпляр класса pmvui.UserInterface
    srcdir  - путь к каталогу.

    Возвращает кортеж из двух элементов:
    1. количество удачно перемещённых или скопированных файлов,
    2. количество файлов, с которыми облом-с."""

    statProcessedFiles = 0
    statSkippedFiles = 0

    for srcroot, dirs, files in os.walk(srcdir):
        if env.showSrcDir:
            ui.job_show_dir(srcroot)

        for fname in files:
            srcPathName = os.path.join(srcroot, fname)
            if os.path.isfile(srcPathName):
                # всякие там символические ссылки пока нафиг
                try:
                    metadata = FileMetadata(srcPathName)
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

                ui.job_progress(0.0, '%s -> %s%s' % (fname, newFileName, newFileExt))

                destPathName = os.path.join(destPath, '%s%s' % (newFileName, newFileExt))

                if os.path.exists(destPathName):
                    if env.ifFileExists == env.FEXIST_SKIP:
                        ui.job_error('файл уже существует, пропускаю')
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
                    skippedFiles += 1
                    ui.job_error(u'не удалось % файл - %s' % (env.modeMessages.errmsg, emsg))

    return (statProcessedFiles, statSkippedFiles)


def process_task(env, ui):
    statProcessedFiles = 0
    statSkippedFiles = 0

    ui.job_begin()

    for srcdir in env.sourceDirs:
        spf, ssf = process_source_dir(env, ui, srcdir)

        statProcessedFiles += spf
        statSkippedFiles += ssf

    ui.job_end('Всего файлов %s: %d, пропущено: %d' % (env.modeMessages.statmsg, statProcessedFiles, statSkippedFiles))


def main(args):
    ui = None
    try:
        mode, gui = Environment.detect_work_mode(args[0])

        if gui:
            from pmvgtkui import GTKUI as UIClass
        else:
            from pmvtermui import TerminalUI as UIClass

        env = Environment(args, mode, gui)

        ui = UIClass(env)
        ui.run(process_task)

    except Exception as ex:
        es = str(ex)

        if ui:
            ui.critical_error(es)
        else:
            print('* Ошибка: %s' % es)

        return 1


    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
