#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Copyright 2017-2020 MC-6312

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


def process_files(env):
    """Обработка исходных каталогов.

    env     - экземпляр pmvconfig.Environment

    Возвращает список строк, содержащих сообщения
    (кол-во обработанных файлов и т.п.)."""

    statTotalFiles = 0
    statProcessedFiles = 0
    statSkippedFiles = 0

    def job_show_dir(dirname=''):
        if env.showSrcDir and dirname:
            print(dirname, file=sys.stderr)

    def job_progress(progress:float, msg=''):
        pg = '' if progress < 0.0 else '%3.1f%% ' % progress

        if msg:
            pg = '%s%s' % (pg, msg)

        if pg:
            print(msg, file=sys.stderr)

    def job_error(msg):
        print('* %s' % msg, file=sys.stderr)

    def job_warning(msg):
        job_error(msg, file=sys.stderr)

    def critical_error(msg):
        print('* %s' % msg, file=sys.stderr)

    def show_fatal_error(msg):
        print('* %s' % msg, file=sys.stderr)

    #
    # 1й проход - подсчет общего количества файлов для индикации прогресса
    # во втором проходе
    #
    env.logger.write_msg(None, 'подготовка')
    job_progress(0.0, 'Подготовка...')

    srcDirs = env.sourceDirs

    # с этим списком будет работать 2й проход
    # содержит он кортежи вида ('каталог', [список файлов]),
    # где список файлов - список строк с именами файлов;
    # да, оно память жрёть, а шо таки делать?
    # а кто натравит photomv на гигантскую файлопомойку -
    # сам себе злой буратино
    sourcedirs = []

    for srcdir in srcDirs:
        if srcdir.ignore:
            continue

        srcdir = srcdir.path

        if not os.path.exists(srcdir) or not os.path.isdir(srcdir):
            emsg = 'путь "%s" не существует или указывает не на каталог' % srcdir
            job_error(emsg)
            env.logger.write_error(None, emsg)
        else:
            for srcroot, dirs, files in os.walk(srcdir):
                # "скрытые" (в *nix-образных ОС) каталоги игнорируем нахрен
                if srcroot.startswith('.'):
                    continue

                flist = [] # список файлов допустимых типов из текущего каталога

                for fname in files:
                    # "скрытые" (в *nix-образных ОС) файлы игнорируем нахрен
                    if fname.startswith('.'):
                        continue

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
    # проход 1.5 - проверка каталога назначения
    # можно было проверить до прохода 1, но с другой стороны -
    # какая нам разница, есть ли каталог назначения, если кидать туда
    # нечего?
    # а вот ща уже есть разница...
    #

    if not env.destinationDir:
        emsg = 'Каталог назначения не указан'
        env.logger.write_error(None, emsg)
        job_error(emsg)
        return

    if env.check_dest_is_same_with_src_dir():
        emsg = 'Каталог назначения совпадает с одним из исходных каталогов'
        env.logger.write_error(None, emsg)
        job_error(emsg)
        return

    # если каталога назначения нет - пытаемся создать.
    # если не удаётся - тогда уже лаемся

    if not os.path.exists(env.destinationDir):
        emsg = make_dirs(destPath, None)
        if emsg:
            env.logger.write(None, env.logger.KW_MKDIR, False, emsg, '')
            job_error(emsg)
            return

    #
    # 2й проход - собственно обработка файлов
    #
    if statTotalFiles:
        nFileIx = 0

        for srcdir, flist in sourcedirs:
            job_show_dir(srcdir)

            for fname in flist:
                nFileIx += 1

                # метка времени для нескольких сообщений при файловых операциях должна быть одинаковой
                timestamp = datetime.datetime.now()

                srcPathName = os.path.join(srcdir, fname)
                if os.path.isfile(srcPathName):
                    # всякие там символические ссылки пока нафиг
                    try:
                        metadata = FileMetadata(srcPathName, env.knownFileTypes)
                    except Exception as ex:
                        statSkippedFiles += 1

                        emsg = 'не удалось получить метаданные файла "%s" - %s' % (fname, str(ex))
                        env.logger.write_error(timestamp, emsg)
                        job_error(emsg)
                        # с кривыми файлами ничего не делаем
                        continue

                    #
                    # выясняем, каким шаблоном создавать новое имя файла
                    #

                    fntemplate = env.get_template(metadata.fields[metadata.MODEL])

                    newSubDir, newFileName, newFileExt = fntemplate.get_new_file_name(env, metadata)

                    destPath = os.path.join(env.destinationDir, newSubDir)

                    emsg = make_dirs(destPath, None)
                    if emsg:
                        env.logger.write(timestamp, env.logger.KW_MKDIR, False, emsg, '')
                        job_error(emsg)
                        return

                    newFileNameExt = newFileName + newFileExt

                    job_progress(float(nFileIx) / statTotalFiles, '%s -> %s' % (fname, newFileNameExt))

                    destPathName = os.path.join(destPath, newFileNameExt)

                    if os.path.exists(destPathName):
                        if env.ifFileExists == env.FEXIST_SKIP:
                            smsg = 'файл "%s" уже существует, пропускаю' % newFileNameExt
                            job_warning(smsg)
                            env.logger.write(timestamp,
                                env.logger.KW_MSG, True, smsg, '')
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
                                emsg = 'в каталоге "%s" слишком много файлов с именем %s*%s' % (destPath, newFileName, newFileExt)
                                job_error(emsg)
                                env.logger.write(timestamp, env.logger.KW_MSG, True, emsg, '')

                                statSkippedFiles += 1
                                continue

                        # else:
                        # env.FEXIST_OVERWRITE - перезаписываем

                    #
                    # а вот теперь копируем или перемещаем файл
                    #

                    fops = env.logger.KW_MV if env.modeMoveFiles else env.logger.KW_CP

                    try:
                        env.modeFileOp(srcPathName, destPathName)
                        fopok = True
                        statProcessedFiles += 1
                    except (IOError, os.error) as emsg:
                        print_exception()
                        statSkippedFiles += 1
                        fopok = False
                        emsg = 'не удалось % файл - %s' % (env.modeMessages.errmsg, repr(emsg))
                        job_error(emsg)
                        env.logger.write_error(timestamp, emsg)

                    env.logger.write(timestamp, fops, fopok, srcPathName, destPathName)

    return ('Всего файлов: %d\n%s: %d\nпропущено: %d' % (statTotalFiles,
        env.modeMessages.statmsg, statProcessedFiles,
        statSkippedFiles),)


def main(args):
    print('%s\n' % TITLE_VERSION)

    try:
        env = Environment()

        #
        # а вот всё последующее логируем
        #
        env.logger.open()
        try:
            env.logger.write_msg(None, '%s' % TITLE_VERSION)

            process_files(env)
        finally:
            env.logger.close()

    except Exception as ex:
        print_exception()

        es = str(ex).strip()
        if not es:
            es = repr(ex)

        show_fatal_error(es)

        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
