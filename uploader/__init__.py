# coding=utf-8
"""
ftp_upload.py
Загружает файлы из home директории проекта по FTP на сервер. Загружает файл сначала в темповое имя, а потом переименовывает его - чтобы не он не обнулялся во время записи.
Передавать имена файлов по argv, поддерживаются несколько файлов сразу. Можно передавать файлы пачками через буфер обмена - он их съест.
Управление загрузкой происходит, если запустить скрипт без аргументов.
Каталоги обрабатывать пока не умеет.

Пример:
ftp_upload.py Z:\home\rosrabota\www\404.htm Z:\home\rosrabota\www\off\ip.php
    Грузит 2 файла себе в список.

ftp_upload.py
    Выдает список загруженных файлов и запрос на команду.
"""
import os
import tempfile
import time

from stack import Stack
from conf import Conf, ConfError, Server

stackPath = tempfile.gettempdir() + '/.uploader.stack'


def info(v):
    print('%s.%r' % (type(v), v))


def split_conf_path(abspath):
    """Разбиваем полный путь к файлу на сервер и относительный путь.
    Если разбиение не получилось (сервер неизвестен), то возвращаем false
    """
    # Попытаться найти .upload.conf.py файл
    path = abspath
    while path != '/':        # TODO: Нужна доработка для WIN-версии
        path = os.path.dirname(path)
        if os.path.exists(path + '/.upload.conf.py'):
            return path, abspath[len(path) + 1:]

    print('Config file .upload.conf.py not found in this directory or parent tree')
    return False


def append_file(stack, confs, abspath):
    """Просто добавляем файл в конец списка

    @param stack    Структура стека с подготовленными для загрузки файлами
    @param confs    Dict конфигураций, создаётся динамически. Нужен, чтобы получить ignore файлов.
    @param abspath  Абсолютный путь добавляемого файла
    """
    assert isinstance(stack, Stack)

    conf_and_path = split_conf_path(abspath)
    if not conf_and_path:
        return False
    conf_path, sub_path = conf_and_path

    if conf_path not in confs:
        confs[conf_path] = Conf(conf_path)
    conf = confs[conf_path]

    # Если попалась директория - включить каждый файл в ней
    if os.path.isdir(abspath):
        for root, dirs, files in os.walk(abspath, topdown=True):  # @UnusedVariable
            if conf.is_ignore(root):
                continue
            for file in files:
                if conf.is_ignore(file):
                    continue
                if not append_file(stack, confs, os.path.abspath(root + '/' + file)):
                    return False
        return True

    # Обрабатываем обычный файл
    stack.append(conf_path, [sub_path])
    return True


def append_files(files):
    """Добавить пачку файлов из массива files.

    Это обертка для append_file()
    """
    assert isinstance(files, list)
    stack = Stack(stackPath)
    confs = {}
    pause = False
    for filename in files:
        print(filename + ': ',)
        if append_file(stack, confs, os.path.abspath(filename)):
            print('OK')
        else:
            pause = True
    stack.save()
    if pause:
        raw_input()


def receive_command():
    """Ожидание и разбор команды от юзера."""

    stack = Stack(stackPath)
    if not stack:
        print('Download stack is empty')
        return False
    # Выводим список файлов для загрузки
    stack.print_data()

    command = raw_input("Enter: upload, 'c': clear list, 'w': watch for changes, ^C: stop > ")

    if command == 'c':
        # Чистим этот список файлов
        stack.clear_and_save()
        return True

    # Load configs
    confs = stack.load_confs()

    if command == 'w':
        # Мониторим файлы и заливаем их на сервер по мере изменения
        watch_command(stack, confs)
        return True

    # Upload files to server/servers in parallel threads
    import threading
    threads = []
    for conf_path, sub_paths in stack.data.iteritems():
        conf = confs[conf_path]
        assert isinstance(conf, Conf)
        for server in conf.servers:
            assert isinstance(server, Server)
            if conf.protocol == 'ssh':
                thread = threading.Thread(target=upload_ssh, args=(conf, server, sub_paths))
            elif conf.protocol == 'ftp':
                thread = threading.Thread(target=upload_ftp, args=(conf, server, sub_paths))
            else:
                raise Exception("Cannot process protocol: " + conf.protocol)
            thread.start()
            threads.append(thread)

    for thread in threads:
        thread.join()
    if len(threads) > 1:
        print('--- all uploads finished ---')
    stack.clear_and_save()
    return True


def upload_ssh(conf, server, sub_paths):
    """Поехали аплоадить файлы на сервак по SSH

    @param conf         Конфигурация аплоада
    @param server       Сервер аплоада
    @param sub_paths    Список файлов для аплоада относительно пути conf.path
    """
    assert isinstance(conf, Conf)
    assert isinstance(server, Server)
    print('Uploading as ' + server.user_host)

    # Параметры tar
    tar_params = ['-C "%s"' % conf.path,
                  '-czf -']
    if server.owner:
        tar_params += ['--owner ' + server.owner]
    if server.group:
        tar_params += ['--group ' + server.group]

    # Make commands
    cmd_tar = 'tar ' + ' '.join(tar_params) + ' ' + ' '.join(sub_paths)
    cmd_ssh_args = (server.ssh_args + ' ') if server.ssh_args else ''
    cmd_ssh = 'ssh ' + cmd_ssh_args + server.user_host
    cmd_untar = 'tar -C "' + server.rootdir + '" -xzf -'
    # ... and run them
    os.system(cmd_tar + ' | ' + cmd_ssh + ' ' + cmd_untar)

    print '--- finished ' + server.user_host + ' ---'


def upload_ftp(conf, server, sub_paths):
    """Поехали аплоадить файлы на сервак по FTP

    @param conf         Конфигурация аплоада
    @param server       Сервер аплоада
    @param sub_paths    Список файлов для аплоада относительно пути conf.path
    """
    assert isinstance(conf, Conf)
    assert isinstance(server, Server)
    from ftplib import FTP
    print('Connecting')
    ftp = FTP(server.host, server.user, server.srv['passwd'])
    ftp.cwd(server.rootdir)

    print 'Uploading'
    for sub_path in sub_paths:
        sub_path_tmp = sub_path + '~'
        print sub_path,
        ftp.storbinary('STOR ' + sub_path_tmp, open(conf.local_path(sub_path), 'rb'))
        ftp.rename(sub_path_tmp, sub_path)
        print '... OK'

    ftp.quit()
    print '--- finished ---'


def watch_command(stack, confs):
    """Наблюдаем за изменениями файлов и заливаем их при изменении.
    Выход из этого режима - ctrl+c

    TODO: настройки owner, group не поддерживаются

    @param stack    Структура стека
    @param confs    Dict конфигураций: {path: Conf}
    """
    from os.path import getmtime

    def upload(conf, sub_path):
        for server in conf.servers:
            assert isinstance(server, Server)
            cmd_ssh = ('scp ' + conf.local_path(sub_path) + ' ' +
                       server.user_host + ':' + server.remote_path(sub_path))
            os.system(cmd_ssh)

    for conf in confs.itervalues():
        assert isinstance(conf, Conf)
        if conf.protocol != 'ssh':
            raise Exception("server protocol must be ssh")

    files = []
    for conf_path, sub_paths in stack.data.iteritems():
        conf = confs[conf_path]
        assert isinstance(conf, Conf)
        for sub_path in sub_paths:
            files.append((conf, sub_path, getmtime(conf.local_path(sub_path))))
            upload(conf, sub_path)

    print 'Watching for changes'

    while True:
        uploaded = False
        for idx, (conf, sub_path, mtime) in enumerate(files):
            local_path = conf.local_path(sub_path)
            new_mtime = getmtime(local_path)
            if new_mtime != mtime:
                print local_path
                # Make commands
                upload(conf, sub_path)

                files[idx] = (conf, sub_path, new_mtime)
                uploaded = True

        if not uploaded:
            time.sleep(1)
