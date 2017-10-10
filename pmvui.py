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


class UserInterface():
    def __init__(self, env, worker):
        """Инициализация междумордия.
        env - экземпляр pmvconfig.Environment
        worker - функция вида worker(env, ui, srcDirs), выполняющая собственно
            работу с файлами
            где:
            env     - экземпляр класса pmvconfig.Environment
            ui      - экземпляром класса UserInterface, из которого
                      вызвана функция (т.е. self)
            srcDirs - список исходных каталогов;
                      если None или пустой список - ф-я должна использовать
                      список env.sourceDirs

            Функция может (и должна) вызывать методы job_xxx() из ui.

            Возвращает список строк (м.б. пустым), которые программа
            отобразит впоследствии.

            В случае ошибок ф-я должна генерировать исключения."""

        self.env = env
        self.worker = worker

    def run(self):
        """Запуск междумордия."""

        raise NotImplementedError('%s.run() not implemented')

    def job_show_dir(self, dirname=''):
        """Отображение текущего каталога."""

        raise NotImplementedError('%s.job_show_dir() not implemented')

    def job_progress(self, progress, msg=''):
        """Отображение прогресса (напр. прогрессбара или процентов),
        а также отображение сообщения.
        progress    - значение прогресса, 0.0-1.0
        msg         - текст сообщения."""

        raise NotImplementedError('%s.job_progress() not implemented')

    def job_error(self, msg):
        """Неблокирующее (немодальное) отображение сообщения об ошибке msg."""

        raise NotImplementedError('%s.job_error() not implemented')

    def job_warning(self, msg):
        """Отображение предупреждения msg."""

        raise NotImplementedError('%s.job_warning() not implemented')

    def critical_error(self, msg):
        """Блокирующее (модальное) отображение сообщения об ошибке msg."""

        raise NotImplementedError('%s.critical_error() not implemented')

    @staticmethod
    def show_fatal_error(msg):
        """Сообщение о критической ошибке.
        Этот метод следует использовать, если ошибка произошла до
        инициализации интерфейса."""

        print('* %s' % msg)

if __name__ == '__main__':
    print('[%s test]' % __file__)
