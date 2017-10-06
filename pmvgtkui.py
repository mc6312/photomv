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
            crndr = Gtk.CellRendererText()
            crndrpar = 'text'
        elif cdtype == Pixbuf:
            crndr = Gtk.CellRendererPixbuf()
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
    PAGE_START, PAGE_JOB, PAGE_FINAL = range(3)

    SDLC_CHECK, SDLC_SRCDIR = range(2)

    def destroy(self, widget, data=None):
        if not self.isWorking:
            Gtk.main_quit()

    def __init__(self, env, worker):
        super().__init__(env, worker)

        self.isWorking = False

        #
        #
        #
        self.window = Gtk.ApplicationWindow(Gtk.WindowType.TOPLEVEL)
        self.window.connect('destroy', self.destroy)

        self.window.set_icon(self.window.render_icon(Gtk.STOCK_EXECUTE, Gtk.IconSize.DIALOG))

        self.iconDirectory = self.window.render_icon(Gtk.STOCK_DIRECTORY, Gtk.IconSize.MENU)
        self.iconError = self.window.render_icon(Gtk.STOCK_DIALOG_ERROR, Gtk.IconSize.MENU)
        self.iconWarning = self.window.render_icon(Gtk.STOCK_DIALOG_WARNING, Gtk.IconSize.MENU)

        self.window.set_title('%s v%s' % (TITLE, VERSION))

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

        # env.sourceDirs
        sdlisthbox = framehbox('Исходные каталоги', True)

        # список исходных каталогов
        sw, self.srcdirlist, self.srcdirlv,\
        _cols, _crndrs = new_list_view((GObject.TYPE_BOOLEAN, False), (GObject.TYPE_STRING, True))

        for sd in env.sourceDirs:
            self.srcdirlist.append((True, sd))

        sdlisthbox.pack_start(sw, True, True, 0)

        # env.destinationDir
        ddirhbox = framehbox('Каталог назначения', False)

        self.destdirentry = Gtk.Entry()
        self.destdirentry.set_editable(False)
        #!!!
        self.destdirentry.set_text(env.destinationDir)

        ddirhbox.pack_start(self.destdirentry, True, True, 0)

        ddbtn = Gtk.Button('…')
        ddirhbox.pack_start(ddbtn, False, False, 0)

        # настройки
        opthbox = framehbox('Параметры', False)

        opthbox.pack_start(Gtk.Label('Существующий файл'), False, False, 0)

        self.cboxifexists = Gtk.ComboBoxText()

        for sieopt in env.FEXISTS_DISPLAY:
            self.cboxifexists.append_text(sieopt)

        self.cboxifexists.set_active(env.ifFileExists)

        opthbox.pack_start(self.cboxifexists, False, False, 0)

        #
        # страница выполнения (PAGE_JOB)
        #
        jobpagebox = Gtk.VBox(spacing=WIDGET_SPACING)
        self.pages.append_page(jobpagebox, None)

        self.dirtxt = Gtk.Label('')
        jobpagebox.pack_start(self.dirtxt, False, False, 0)

        self.msgtxt = Gtk.Label('')
        jobpagebox.pack_start(self.msgtxt, False, False, 0)

        self.errortxt = Gtk.Label('')
        jobpagebox.pack_end(self.errortxt, False, False, 0)

        self.progbar = Gtk.ProgressBar()
        self.progbar.set_show_text(True)
        jobpagebox.pack_end(self.progbar, False, False, 0)

        #
        # финальная страница (PAGE_FINAL)
        #

        finpagebox = Gtk.VBox(spacing=WIDGET_SPACING)
        self.pages.add(finpagebox)

        self.finaltext = Gtk.Label('Конец мучениям')
        finpagebox.pack_start(self.finaltext, True, True, 0)

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

        self.window.show_all()

    def exec_job(self):
        self.ctlhbox.set_sensitive(False)
        try:
            self.btnstart.set_sensitive(False)
            self.btnstart.set_visible(False)

            self.pages.set_current_page(self.PAGE_JOB)

            try:
                fmsgs = self.worker(self.env, self)

                self.finaltext.set_text('\n'.join(fmsgs))

                es = None
            except Exception as ex:
                es = 'Ошибка: %s' % str(ex)

            if es:
                self.finaltext.set_text(es)

            self.pages.set_current_page(self.PAGE_FINAL)

        finally:
            #self.progbar.set_fraction(1.0)
            self.ctlhbox.set_sensitive(True)
            #self.destroy(btn)

    def run(self):
        Gtk.main()

    def task_events(self):
        # даем прочихаться междумордию
        while Gtk.events_pending():
            Gtk.main_iteration()

    def job_show_dir(self, dirname=''):
        if self.env.showSrcDir and dirname:
            self.dirtxt.set_text(dirname)

    def job_progress(self, progress, msg=''):
        self.progbar.set_text(msg)
        if progress < 0.0:
            self.progbar.pulse()
        else:
            self.progbar.set_fraction(progress)
        self.task_events()

    def job_error(self, msg):
        self.errortxt.set_text(msg)

    def job_warning(self, msg):
        self.errortxt.set_text(msg)

    def critical_error(self, msg):
        msg_dialog(self.window, self.window.get_title(), msg)


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
            for i in range(10):
                ui.job_show_dir('directory')

                #raise ValueError('test exception')

                pg = i / 10.0
                ui.job_progress(pg, 'working, %.1g' % pg)
                sleep(1)

            return ['Проверочное', 'сообщение']

        except Exception as ex:
            ui.critical_error(str(ex))

    env = Environment(['photomv'], True, True)
    ui = GTKUI(env, worker)

    try:
        ui.run()
    except Exception as ex:
        ui.critical_error(str(ex))
