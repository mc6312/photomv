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


class GTKUI(UserInterface):
    def destroy(self, widget, data=None):
        Gtk.main_quit()

    def __init__(self, env, worker):
        super().__init__(env, worker)

        self.window = Gtk.ApplicationWindow(Gtk.WindowType.TOPLEVEL)
        self.window.connect('destroy', self.destroy)

        self.window.set_title('%s v%s' % (TITLE, VERSION))

        self.window.set_size_request(600, -1)
        self.window.set_border_width(WIDGET_SPACING)

        rootvbox = Gtk.VBox(spacing=WIDGET_SPACING)
        self.window.add(rootvbox)

        self.dirtxt = Gtk.Label('')
        rootvbox.pack_start(self.dirtxt, False, False, 0)

        self.msgtxt = Gtk.Label('')
        rootvbox.pack_start(self.msgtxt, False, False, 0)

        self.progbar = Gtk.ProgressBar()
        rootvbox.pack_start(self.progbar, False, False, 0)

        self.errortxt = Gtk.Label('')
        rootvbox.pack_start(self.errortxt, False, False, 0)

        self.ctlhbox = Gtk.HBox(spacing=WIDGET_SPACING)

        btnstart = Gtk.Button('Начать')
        btnstart.connect('clicked', self.btnstart_clicked)
        self.ctlhbox.pack_start(btnstart, False, False, 0)

        btnexit = Gtk.Button('Выход')
        btnexit.connect('clicked', self.destroy)
        self.ctlhbox.pack_end(btnexit, False, False, 0)

        rootvbox.pack_end(self.ctlhbox, False, False, 0)

        self.window.show_all()

    def btnstart_clicked(self, btn):
        self.worker(self.env, self)
        msg_dialog(self.window, self.window.get_title(), 'Опа!', msgtype=Gtk.MessageType.INFO)
        self.destroy(btn)

    def run(self):
        Gtk.main()

    def task_events(self):
        # даем прочихаться междумордию
        while Gtk.events_pending():
            Gtk.main_iteration()

    def job_begin(self, msg=''):
        self.ctlhbox.set_sensitive(False)
        self.msgtxt.set_text(msg)

    def job_show_dir(self, dirname=''):
        self.dirtxt.set_text(dirname)

    def job_progress(self, progress, msg=''):
        self.msgtxt.set_text(msg)
        self.progbar.set_fraction(progress)
        self.task_events()

    def job_end(self, msg=''):
        self.msgtxt.set_text(msg)
        self.progbar.set_fraction(1.0)
        self.ctlhbox.set_sensitive(True)

    def job_error(self, msg):
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
        ui.job_begin('Begin')
        try:
            try:
                for i in range(10):
                    ui.job_show_dir('directory')

                    #raise ValueError('test exception')

                    pg = i / 10.0
                    ui.job_progress(pg, 'working, %.1g' % pg)
                    sleep(1)
            except Exception as ex:
                ui.critical_error(str(ex))
        finally:
            ui.job_end('End')

    env = Environment(['photomv'], True, True)
    ui = GTKUI(env, worker)

    try:
        ui.run()
    except Exception as ex:
        ui.critical_error(str(ex))
