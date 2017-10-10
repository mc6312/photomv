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

from gi import require_version as gi_require_version
gi_require_version('Gtk', '3.0') # извращенцы
from gi.repository import Gtk, Gdk, GObject, Pango, GLib
from gi.repository.GdkPixbuf import Pixbuf


WIDGET_SPACING = 4


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


def new_list_view(*coldefs):
    """Создаёт Gtk.TreeView.

    coldefs - один или несколько кортежей.
    Кортежи должны содержать по два элемента:
    1. тип данных GObject.TYPE_xxx
    2. булевское значение: должен ли столбец автоматически расширяться
       до макс. ширины.

    Возвращает кортеж из следующих элементов:
    экземпляры Gtk.ScrolledWindow, Gtk.ListStore, Gtk.TreeView,
    список экземпляров Gtk.TreeViewColumn, список экземпляров Gtk.CellRenderer."""

    lstore = Gtk.ListStore(*map(lambda cd: cd[0], coldefs))

    lview = Gtk.TreeView(lstore)
    lview.set_headers_visible(False)

    columns = []
    renderers = []

    for colix, (cdtype, cexpand) in enumerate(coldefs):
        if cdtype == GObject.TYPE_BOOLEAN:
            crndr = Gtk.CellRendererToggle()
            crndrpar = 'active'
        elif cdtype == GObject.TYPE_STRING:
            crndr = Gtk.CellRendererText(wrap_mode=Pango.WrapMode.WORD_CHAR)
            crndrpar = 'text'
        elif cdtype == Pixbuf:
            crndr = Gtk.CellRendererPixbuf()
            crndr.set_alignment(0.0, 0.0)
            crndrpar = 'pixbuf'
        else:
            raise ValueError('new_list_view(): invalid type of column %d' % colix)

        col = Gtk.TreeViewColumn('', crndr)
        col.add_attribute(crndr, crndrpar, colix)
        col.set_sizing(Gtk.TreeViewColumnSizing.GROW_ONLY)
        col.set_resizable(False)
        col.set_expand(cexpand)
        lview.append_column(col)

        columns.append(col)
        renderers.append(crndr)

    sw = Gtk.ScrolledWindow()
    sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    sw.set_shadow_type(Gtk.ShadowType.IN)
    sw.add(lview)

    return (sw, lstore, lview, columns, renderers)


class GTKUI(UserInterface):
    PAGE_START, PAGE_JOB = range(2)

    SDLC_CHECK, SDLC_SRCDIR = range(2)

    MAX_MESSAGES = 2000

    def destroy(self, widget, data=None):
        Gtk.main_quit()

    def delete_event(self, widget, event):
        # блокируем кнопку закрытия, пока задание не завершилось
        return self.isWorking

    def __init__(self, env, worker):
        super().__init__(env, worker)

        self.isWorking = False

        #
        #
        #
        self.window = Gtk.ApplicationWindow(Gtk.WindowType.TOPLEVEL)
        self.window.connect('destroy', self.destroy)
        self.window.connect('delete-event', self.delete_event)

        self.window.set_icon(self.window.render_icon(Gtk.STOCK_EXECUTE, Gtk.IconSize.DIALOG))

        self.iconDirectory = self.window.render_icon(Gtk.STOCK_DIRECTORY, Gtk.IconSize.MENU)
        self.iconError = self.window.render_icon(Gtk.STOCK_DIALOG_ERROR, Gtk.IconSize.MENU)
        self.iconWarning = self.window.render_icon(Gtk.STOCK_DIALOG_WARNING, Gtk.IconSize.MENU)

        self.window.set_title(TITLE_VERSION)

        _b, icx, icy = Gtk.IconSize.lookup(Gtk.IconSize.SMALL_TOOLBAR)

        self.window.set_size_request(icx * 42, icx * 22) # шоб не совсем уж от балды
        self.window.set_border_width(WIDGET_SPACING)

        rootvbox = Gtk.VBox(spacing=WIDGET_SPACING)
        self.window.add(rootvbox)

        self.pages = Gtk.Notebook(show_tabs=False, show_border=False)
        rootvbox.pack_start(self.pages, True, True, 0)

        #
        # начальная страница (PAGE_START)
        #
        startpagebox = Gtk.VBox(spacing=WIDGET_SPACING)
        self.pages.append_page(startpagebox, None)

        def framehbox(label, expand):
            fr = Gtk.Frame.new(label)
            startpagebox.pack_start(fr, expand, expand, 0)

            hbox = Gtk.HBox(spacing=WIDGET_SPACING)
            hbox.set_border_width(WIDGET_SPACING)
            fr.add(hbox)

            return hbox

        #
        # режим
        #

        modebox = Gtk.HBox(spacing=WIDGET_SPACING)
        startpagebox.pack_start(modebox, False, False, 0)

        modebox.pack_start(Gtk.Label('Режим:'), False, False, 0)

        moderbtncopy = Gtk.RadioButton.new_with_label(None, 'копирование')
        moderbtncopy.connect('toggled', self.moderbtn_toggled, False)
        modebox.pack_start(moderbtncopy, False, False, 0)

        moderbtnmove = Gtk.RadioButton.new_with_label_from_widget(moderbtncopy, 'перемещение')
        moderbtnmove.connect('toggled', self.moderbtn_toggled, True)
        modebox.pack_start(moderbtnmove, False, False, 0)

        rbtn = moderbtnmove if self.env.modeMoveFiles else moderbtncopy
        rbtn.set_active(self.env.modeMoveFiles)

        #
        # env.sourceDirs
        #
        sdlisthbox = framehbox('Исходные каталоги', True)

        # список исходных каталогов
        sw, self.srcdirlist, self.srcdirlv,\
        _cols, _crndrs = new_list_view((GObject.TYPE_BOOLEAN, False), (GObject.TYPE_STRING, True))
        self.srcdirlvsel = self.srcdirlv.get_selection()

        for sd in env.sourceDirs:
            self.srcdirlist.append((True, sd))

        sdlisthbox.pack_start(sw, True, True, 0)

        sdlistvbox = Gtk.VBox(spacing=WIDGET_SPACING)
        sdlisthbox.pack_end(sdlistvbox, False, False, 0)

        for sicon, handler in (('edit-add', self.sdlist_add), ('edit-delete', self.sdlist_delete)):
            btn = Gtk.Button.new_from_icon_name(sicon, Gtk.IconSize.SMALL_TOOLBAR)
            btn.connect('clicked', handler)
            sdlistvbox.pack_start(btn, False, False, 0)

        # env.destinationDir
        ddirhbox = framehbox('Каталог назначения', False)

        self.destdirentry = Gtk.Entry()
        self.destdirentry.set_editable(False)
        #!!!
        self.destdirentry.set_text(env.destinationDir)

        ddirhbox.pack_start(self.destdirentry, True, True, 0)

        ddbtn = Gtk.Button('…')
        ddbtn.connect('clicked', self.ddbtn_clicked)
        ddirhbox.pack_start(ddbtn, False, False, 0)

        # настройки
        opthbox = framehbox('Параметры', False)

        opthbox.pack_start(Gtk.Label('Существующий файл'), False, False, 0)

        self.cboxifexists = Gtk.ComboBoxText()

        for sieopt in env.FEXISTS_DISPLAY:
            self.cboxifexists.append_text(sieopt)

        self.cboxifexists.set_active(env.ifFileExists)
        self.cboxifexists.connect('changed', self.cboxifexists_changed)

        opthbox.pack_start(self.cboxifexists, False, False, 0)

        #
        # страница выполнения (PAGE_JOB)
        #
        jobpagebox = Gtk.VBox(spacing=WIDGET_SPACING)
        self.pages.append_page(jobpagebox, None)

        sw, self.msglstore, self.msglview,\
        _cls, _crs = new_list_view((Pixbuf, False), (GObject.TYPE_STRING, True))
        self.msglvsel = self.msglview.get_selection()

        jobpagebox.pack_start(sw, True, True, 0)

        self.progbar = Gtk.ProgressBar()
        self.progbar.set_show_text(True)
        jobpagebox.pack_end(self.progbar, False, False, 0)

        #
        # управление
        #

        self.ctlhbox = Gtk.HBox(spacing=WIDGET_SPACING)
        rootvbox.pack_end(self.ctlhbox, False, False, 0)

        self.btnstart = Gtk.Button('Начать')
        self.btnstart.connect('clicked', lambda b: self.exec_job())
        self.ctlhbox.pack_start(self.btnstart, False, False, 0)

        btnexit = Gtk.Button('Выход')
        btnexit.connect('clicked', self.destroy)
        self.ctlhbox.pack_end(btnexit, False, False, 0)
        #
        self.pages.set_current_page(self.PAGE_START)

        self.window.show_all()

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
                self.env.sourceDirs.append(sdir)
                self.srcdirlist.append((True, sdir))

    def get_selected_srcdir_iter(self):
        return self.srcdirlvsel.get_selected()[1]

    def sdlist_delete(self, btn):
        itrs = self.get_selected_srcdir_iter()
        if itrs:
            ix = self.srcdirlist.get_path(itrs).get_indices()[0]
            del self.env.sourceDirs[ix]
            self.srcdirlist.remove(itrs)

    def cboxifexists_changed(self, cbox):
        self.env.ifFileExists = cbox.get_active()

    def ddbtn_clicked(self, btn):
        SDDIR = 'Каталог назначения'

        ddir = choose_directory(self.window, SDDIR, True, env.destinationDir)
        if ddir:
            if self.env.same_src_dir(ddir):
                msg_dialog(self.window, SDDIR,
                    'Выбранный каталог совпадает с одним из исходных каталогов',
                    Gtk.MessageType.ERROR)
            else:
                self.env.destinationDir = ddir
                self.destdirentry.set_text(ddir)

    def moderbtn_toggled(self, rbtn, modeMove):
        if rbtn.get_active():
            self.env.modeMoveFiles = modeMove

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

        try:
            self.btnstart.set_sensitive(False)
            self.btnstart.set_visible(False)

            self.pages.set_current_page(self.PAGE_JOB)

            try:
                fmsgs = self.worker(self.env, self)

                for msg in fmsgs:
                    self.job_message(None, msg)

            except Exception as ex:
                self.job_error('Ошибка: %s' % str(ex))

        finally:
            self.progbar.set_fraction(0.0)
            self.progbar.set_text('')
            self.ctlhbox.set_sensitive(True)
            self.isWorking = False
            #self.destroy(btn)

    def run(self):
        Gtk.main()

    def task_events(self):
        # даем прочихаться междумордию
        while Gtk.events_pending():
            Gtk.main_iteration()

    def job_show_dir(self, dirname=''):
        if self.env.showSrcDir and dirname:
            self.job_message(self.iconDirectory, dirname)

    def job_progress(self, progress, msg=''):
        self.progbar.set_text(msg)
        if progress < 0.0:
            self.progbar.pulse()
        else:
            self.progbar.set_fraction(progress)
        self.task_events()

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
            ui.job_error(str(ex))
            return []

    env = Environment(['photomvg'])
    env.showSrcDir = True
    ui = GTKUI(env, worker)

    try:
        ui.run()
    except Exception as ex:
        ui.critical_error(str(ex))
