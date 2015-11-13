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

from structure import *

stackPath = tempfile.gettempdir() + '/.uploader.stack'


def split_conf_path(abspath):
    """Разбиваем полный путь к файлу на сервер и относительный путь.
    Если разбиение не получилось (сервер неизвестен), то возвращаем false
    """
    # Попытаться найти .upload.conf.py файл
    path = abspath
    while path != '/':
        path = os.path.dirname(path)
        if os.path.exists(path + '/.upload.conf.py'):
            return path, abspath[len(path) + 1:]
    return False


def append_file(stack, confs, abs_path):
    """Просто добавляем файл в конец списка

    @param stack                Структура стека с подготовленными для загрузки файлами
    @param confs                Dict конфигураций, создаётся динамически. Нужен, чтобы получить ignore файлов.
    @param abs_path             Абсолютный путь добавляемого файла или каталога
    """
    assert isinstance(stack, Stack)
    if not os.path.exists(abs_path):
        raise ConfError('File ' + abs_path + ' does not exist')

    conf_and_path = split_conf_path(abs_path)
    if not conf_and_path:
        raise ConfError('Config file .upload.conf.py not found in this directory or parent tree')
    conf_path, sub_path = conf_and_path

    if conf_path not in confs:
        confs[conf_path] = Conf(conf_path)
    conf = confs[conf_path]
    assert isinstance(conf, Conf)

    stack_item = StackItem.from_sub_path(sub_path)
    if conf.is_ignore(os.path.basename(stack_item.pure_path)):
        return True
    stack_item.server_filter.validate(conf)

    # Если попалась директория - включить каждый файл в ней
    if os.path.isdir(abs_path):
        for sub_path in os.listdir(abs_path):
            append_file(stack, confs, abs_path + '/' + sub_path)
    else:
        stack.append(conf_path, stack_item)


def append_files(files):
    """Добавить пачку файлов из массива files.

    Это обертка для append_file()
    """
    assert isinstance(files, list)
    stack = Stack(stackPath)
    confs = {}
    for filename in files:
        print filename + ': ',
        append_file(stack, confs, os.path.abspath(filename))
        print('OK')
    stack.save()


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
    was_error = [False]
    def safe_run(fn):
        try:
            fn()
        except:
            # Код ниже стопорит скрипт, если случилась ошибка. Чтобы можно было посмотреть что там такое.
            was_error[0] = True
            import traceback
            traceback.print_exc()

    import threading
    threads = []
    for conf_path, stack_items in stack.data.iteritems():
        conf = confs[conf_path]
        assert isinstance(conf, Conf)
        for server in conf.servers:
            assert isinstance(server, Server)
            items = filter(lambda v: server in v.server_filter, stack_items)

            if items:
                if conf.protocol == 'ssh':
                    thread = threading.Thread(target=safe_run, args=(lambda: upload_ssh(conf, server, items),))
                elif conf.protocol == 'ftp':
                    thread = threading.Thread(target=safe_run, args=(lambda: upload_ftp(conf, server, items),))
                else:
                    raise Exception("Cannot process protocol: " + conf.protocol)
                thread.start()
                threads.append(thread)

    for thread in threads:
        thread.join()
    if was_error[0]:
        return False
    else:
        if len(threads) > 1:
            print('--- all uploads finished ---')
        stack.clear_and_save()
        return True


def upload_ssh(conf, server, stack_items):
    """Поехали аплоадить файлы на сервак по SSH

    @param conf             Конфигурация аплоада
    @param server           Сервер аплоада
    @param stack_items      List of StackItem for upload
    """
    import io
    import tarfile
    import subprocess
    assert isinstance(conf, Conf)
    assert isinstance(server, Server)
    print('Uploading as ' + server.user_host)

    ssh_args = ['/usr/bin/ssh']
    if server.ssh_args:
        ssh_args += server.ssh_args
    ssh_args += [server.user_host, 'tar', '-C', server.rootdir, '-xzf', '-']
    ssh_process = subprocess.Popen(ssh_args, stdin=subprocess.PIPE)

    with tarfile.open(mode="w|gz",
                      fileobj=ssh_process.stdin,
                      encoding='utf-8') as tar:
        assert isinstance(tar, tarfile.TarFile)
        for stack_item in stack_items:
            abspath = conf.local_path(stack_item.sub_path)
            tarinfo = tar.gettarinfo(abspath, arcname=stack_item.pure_path)
            assert isinstance(tarinfo, tarfile.TarInfo)
            if server.owner:
                if isinstance(server.owner, int):
                    tarinfo.uid = server.owner
                else:
                    tarinfo.uname = server.owner
            if server.group:
                if isinstance(server.group, int):
                    tarinfo.gid = server.group
                else:
                    tarinfo.gname = server.group
            tar.addfile(tarinfo, io.FileIO(abspath))
        tar.close()
    ssh_process.stdin.close()
    ssh_process.wait()

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

    def upload(conf, sub_path, server_filter, opts):
        for server in conf.servers:
            assert isinstance(server, Server)
            if server in server_filter:
                cmd_ssh = ('scp ' + conf.local_path(sub_path) + ' ' +
                           server.user_host + ':' + server.remote_path(sub_path))
                os.system(cmd_ssh)

    for conf in confs.itervalues():
        assert isinstance(conf, Conf)
        if conf.protocol != 'ssh':
            raise Exception("server protocol must be ssh")

    files = []
    for conf_path, sub_path_rows in stack.data.iteritems():
        conf = confs[conf_path]
        assert isinstance(conf, Conf)
        for sub_path, server_filter, opts in sub_path_rows:
            files.append((conf, sub_path, server_filter, opts, getmtime(conf.local_path(sub_path))))
            upload(conf, sub_path, server_filter, opts)

    print 'Watching for changes'

    while True:
        uploaded = False
        for idx, (conf, sub_path, server_filter, opts, mtime) in enumerate(files):
            local_path = conf.local_path(sub_path)
            new_mtime = getmtime(local_path)
            if new_mtime != mtime:
                print local_path
                # Make commands
                upload(conf, sub_path, server_filter, opts)

                files[idx] = (conf, sub_path, new_mtime)
                uploaded = True

        if not uploaded:
            time.sleep(1)
