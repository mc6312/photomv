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

from gtktools import *

from gi.repository import Gtk, Gdk, GObject, Pango, GLib
from gi.repository.GdkPixbuf import Pixbuf


def choose_directory(parent, title, create, dirpath=None):
    """Диалог выбора каталога.

    parent  - экземпляр Gtk.Window
    title   - строка заголовка
    create  - булевское значение: создавать ли каталог
    dirpath - каталог, с которого начинать выбор
              или None.

    При выборе каталога и нажатии "ОК" возвращает выбранный каталог,
    иначе возвращает None."""

    dlg = Gtk.FileChooserDialog(title, parent,
        Gtk.FileChooserAction.SELECT_FOLDER,
        (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK))
    dlg.set_create_folders(create)

    if dirpath:
        dlg.set_current_folder(dirpath)

    ret = None
    r = dlg.run()

    if r == Gtk.ResponseType.OK:
        ret = dlg.get_current_folder()

    dlg.destroy()

    return ret


class GTKUI(UserInterface):
    PAGE_START, PAGE_JOB = range(2)

    SDLC_CHECK, SDLC_SRCDIR = range(2)

    MAX_MESSAGES = 2000

    def destroy(self, widget, data=None):
        self.env.save()
        Gtk.main_quit()

    def delete_event(self, widget, event):
        # блокируем кнопку закрытия, пока задание не завершилось
        return self.isWorking

    def __init__(self, env, worker):
        super().__init__(env, worker)

        self.isWorking = False

        resldr = get_resource_loader()
        uibldr = get_gtk_builder(resldr, 'photomv.ui')
        #
        #
        #
        self.window = uibldr.get_object('wndMain')

        _b, icx, icy = Gtk.IconSize.lookup(Gtk.IconSize.DIALOG)
        wicon = resldr.load_pixbuf('photomv.svg', icx, icy, Gtk.STOCK_EXECUTE)

        self.window.set_icon(wicon)

        self.iconDirectory = self.window.render_icon(Gtk.STOCK_DIRECTORY, Gtk.IconSize.MENU)
        self.iconError = self.window.render_icon(Gtk.STOCK_DIALOG_ERROR, Gtk.IconSize.MENU)
        self.iconWarning = self.window.render_icon(Gtk.STOCK_DIALOG_WARNING, Gtk.IconSize.MENU)

        self.window.set_title(TITLE_VERSION)

        _b, icx, icy = Gtk.IconSize.lookup(Gtk.IconSize.SMALL_TOOLBAR)

        self.window.set_size_request(icx * 42, icx * 22) # шоб не совсем уж от балды
        self.window.set_border_width(WIDGET_SPACING)

        self.pages = uibldr.get_object('pages')

        #
        # начальная страница (PAGE_START)
        #

        #
        # режим
        #

        moderbtncopy = uibldr.get_object('moderbtncopy')
        moderbtnmove = uibldr.get_object('moderbtnmove')

        rbtn = moderbtnmove if self.env.modeMoveFiles else moderbtncopy
        rbtn.set_active(self.env.modeMoveFiles)

        #
        # env.sourceDirs
        #

        # список исходных каталогов
        self.srcdirlist = uibldr.get_object('srcdirlist')
        self.srcdirlv = uibldr.get_object('srcdirlv')
        self.srcdirlvsel = self.srcdirlv.get_selection()

        for sd in self.env.sourceDirs:
            self.srcdirlist.append((not sd.ignore, sd.path))

        # env.destinationDir

        self.destdirbutton = uibldr.get_object('destdirbutton')
        self.destdirbutton.select_filename(self.env.destinationDir)

        #
        # настройки
        #

        # обработка существующих файлов

        self.cboxifexists = uibldr.get_object('cboxifexists')

        for sieopt in env.FEXISTS_DISPLAY:
            self.cboxifexists.append_text(sieopt)

        self.cboxifexists.set_active(env.ifFileExists)

        # поведение при завершении
        chkexitok = uibldr.get_object('chkexitok')
        chkexitok.set_active(env.closeIfSuccess)

        #
        # страница выполнения (PAGE_JOB)
        #

        self.msglstore = uibldr.get_object('msglstore')
        self.msglview = uibldr.get_object('msglview')
        self.msglvsel = self.msglview.get_selection()

        self.progbar = uibldr.get_object('progbar')

        #
        # управление
        #

        self.ctlhbox = uibldr.get_object('ctlhbox')

        self.btnstart = uibldr.get_object('btnstart')

        self.window.set_default(self.btnstart) #? glade сюда не умеет ?

        self.btnexit = uibldr.get_object('btnexit')
        #
        self.pages.set_current_page(self.PAGE_START)

        uibldr.connect_signals(self)
        self.window.show_all()

    def btnstart_clicked_cb(self, btn):
        self.exec_job()

    def sdlist_add(self, btn):
        SSDIR = 'Исходный каталог'

        sdir = choose_directory(self.window, SSDIR, False)
        if sdir:
            if self.env.same_src_dir(sdir):
                msg_dialog(self.window, SSDIR,
                    'Выбранный каталог совпадает с одним из исходных каталогов',
                    Gtk.MessageType.ERROR)
            elif same_dir(sdir, self.env.destinationDir):
                msg_dialog(self.window, SSDIR,
                    'Выбранный каталог совпадает с каталогом назначения',
                    Gtk.MessageType.ERROR)
            else:
                self.env.sourceDirs.append(self.env.SourceDir(sdir, True))
                self.srcdirlist.append((True, sdir))

        self.btnstart.set_sensitive(len(self.env.sourceDirs) > 0)

    def sdlist_delete(self, btn):
        n = self.srcdirlist.iter_n_children(None)
        if n < 2:
            msg_dialog(self.window, 'Удаление каталога из списка',
                'Единственный элемент списка не может быть удалён.',
                Gtk.MessageType.WARNING)
            return

        itrs = self.get_selected_srcdir_iter()
        if itrs:
            ix = self.srcdirlist.get_path(itrs).get_indices()[0]
            del self.env.sourceDirs[ix]
            self.srcdirlist.remove(itrs)

            self.btnstart.set_sensitive(len(self.env.sourceDirs) > 0)

    def sdlist_row_activated(self, tv, path, col):
        itr = self.srcdirlist.get_iter(path)
        #colix = self.srcdirlvcols.index(col)
        # пока плюём на номер столбца
        chk = self.srcdirlist.get(itr, self.SDLC_CHECK)[0]
        self.srcdirlist.set_value(itr, self.SDLC_CHECK, not chk)
        self.env.sourceDirs[path.get_indices()[0]].ignore = chk

    def chkexitok_toggled(self, btn, data=None):
        self.env.closeIfSuccess = btn.get_active()

    def get_selected_srcdir_iter(self):
        return self.srcdirlvsel.get_selected()[1]

    def cboxifexists_changed(self, cbox):
        self.env.ifFileExists = cbox.get_active()

    def destdirbutton_file_set_cb(self, btn):
        ddir = self.destdirbutton.get_filename() # get_current_folder?

        if ddir:
            if self.env.same_src_dir(ddir):
                msg_dialog(self.window, self.destdirbutton.get_title(),
                    'Выбранный каталог совпадает с одним из исходных каталогов',
                    Gtk.MessageType.ERROR)

                # возвращаем взад старое значение, а то FileChooserButton про неправильные каталоги ничего же не знает
                self.destdirbutton.select_filename(self.env.destinationDir)
            else:
                self.env.destinationDir = ddir

    def moderbtncopy_toggled_cb(self, rbtn):
        self.env.modeMoveFiles = not rbtn.get_active()

    def moderbtnmove_toggled_cb(self, rbtn):
        self.env.modeMoveFiles = rbtn.get_active()

    def job_message(self, icon, txt):
        self.msglstore.append((icon, txt))

        count = self.msglstore.iter_n_children(None)
        if count > self.MAX_MESSAGES:
            self.msglstore.remove(self.msglstore.get_iter_first())
            count -= 1

        last = self.msglstore.iter_nth_child(None, count - 1)

        self.msglvsel.select_iter(last)
        self.msglview.scroll_to_cell(self.msglstore.get_path(last),
            None, False, 0, 0)

    def exec_job(self):
        self.ctlhbox.set_sensitive(False)
        self.isWorking = True

        self.env.setup_work_mode()
        self.env.save()

        nErrors = 0

        try:
            self.btnstart.set_sensitive(False)
            self.btnstart.set_visible(False)

            self.pages.set_current_page(self.PAGE_JOB)

            try:
                fmsgs = self.worker(self.env, self)

                for msg in fmsgs:
                    self.job_message(None, msg)

            except Exception as ex:
                print_exception()
                self.job_error('Ошибка: %s' % repr(ex))

                nErrors += 1

            if not nErrors and self.env.closeIfSuccess:
                self.destroy(None)

        finally:
            self.progbar.set_fraction(0.0)
            self.progbar.set_text('')
            self.ctlhbox.set_sensitive(True)
            self.window.set_default(self.btnexit)
            self.isWorking = False

    def run(self):
        Gtk.main()

    def job_show_dir(self, dirname=''):
        if self.env.showSrcDir and dirname:
            self.job_message(self.iconDirectory, dirname)

    def job_progress(self, progress, msg=''):
        self.progbar.set_text(msg)
        if progress < 0.0:
            self.progbar.pulse()
        else:
            self.progbar.set_fraction(progress)

        flush_gtk_events()

    def job_error(self, msg):
        self.job_message(self.iconError, msg)

    def job_warning(self, msg):
        self.job_message(self.iconWarning, msg)

    def critical_error(self, msg):
        msg_dialog(self.window, self.window.get_title(), msg)

    @staticmethod
    def show_fatal_error(msg):
        msg_dialog(None, '%s - ошибка' % TITLE_VERSION, msg, Gtk.MessageType.ERROR)


def msg_dialog(parent, title, msg, msgtype=Gtk.MessageType.WARNING, buttons=Gtk.ButtonsType.OK):
    dlg = Gtk.MessageDialog(parent, 0, msgtype, buttons, msg)
    dlg.set_title(title)
    r = dlg.run()
    dlg.destroy()
    return r


if __name__ == '__main__':
    print('[%s test]' % __file__)

    from time import sleep

    def worker(env, ui):
        try:
            N = 20
            for i in range(N):
                ui.job_show_dir('directory #%d\nsome text' % i)

                #raise ValueError('test exception')

                pg = float(i) / N
                ui.job_progress(pg, 'working, %.1g' % pg)
                sleep(0.5)

            return ['Проверочное', 'сообщение']

        except Exception as ex:
            #ui.critical_error(str(ex))
            print_exception()
            ui.job_error(str(ex))
            return []

    env = Environment(['photomvg'])
    if env.error:
        raise Exception(env.error)

    env.showSrcDir = True
    ui = GTKUI(env, worker)

    try:
        ui.run()
    except Exception as ex:
        print_exception()
        ui.critical_error(str(ex))
