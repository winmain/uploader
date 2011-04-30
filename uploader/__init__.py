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
import sys, os, re, imp, tempfile

baseStackPath = tempfile.gettempdir() + '/.uploader.stack'
localhome_dir = '/srv/'
servers = {
    'example': {
        'host':     '127.0.0.1',
        'user':     'login',
        'passwd':   'password',
        'rootdir':  '/www/htdocs/',
    },
}

# Добавим дополнительные серверы
if os.path.exists(ur'C:\home\.docs\Логин\hosts\ftp_upload-hosts.py'):
    more_servers = imp.load_source('more_servers', ur'C:\home\.docs\Логин\hosts\ftp_upload-hosts.py'.encode('cp1251'))
    servers.update(more_servers.servers)
if os.path.exists(os.path.expanduser('~/ftp_upload-hosts.py')):
    more_servers = imp.load_source('more_servers', os.path.expanduser('~/ftp_upload-hosts.py'))
    servers.update(more_servers.servers)


def info(v):
    print '%s.%r' % (type(v), v)


def adopt(abspath):
    """Разбиваем полный путь к файлу на сервер и относительный путь.
    Если разбиение не получилось (сервер неизвестен), то возвращаем false
    """

    if not os.path.isfile(abspath):
        print "It's not a file"
        return False

    result = \
        re.search(r'/home/([^/]*)/(.+)$', abspath) \
        or re.search(r'[\\/]KrasPrice[\\/]([^\\/]*)[\\/](.+)$', abspath)
    if not result:
        print 'You are not in home dir'
        return False
    host = result.group(1)
    localpath = result.group(2)
    if host not in servers:
        # Попытаться найти .upload.conf.py файл
        path = abspath
        while path != '/':        # TODO: Нужна доработка для WIN-версии
            path = os.path.dirname(path)
            if os.path.exists(path + '/.upload.conf.py'):
                return path.replace('/', '|'), abspath[len(path) + 1:]

        print 'Unknown server: ' + host
        return False
    return host, localpath


def append_file(append):
    """Просто добавляем файл в конец списка

    TODO: организовать проверку на старость стек-файла (более 1 дня)
    """

    abspath = os.path.abspath(append)
    # Если попалась директория - включить каждый файл в ней
    if os.path.isdir(abspath):
        for root, dirs, files in os.walk(os.path.abspath(append), topdown=True): #@UnusedVariable
            if '.svn' in root or '.hg' in root:
                continue
            for file in files:
                if not append_file(root + '/' + file):
                    return False
        return True

    # Обрабатываем обычный файл
    append = adopt(os.path.abspath(append))
    if not append:
        return False
    host, localpath = append
    local_stackfile = baseStackPath + '.' + host

    if os.path.exists(local_stackfile):
        f = open(local_stackfile)
        for line in f:
            if line.rstrip() == localpath:   # Если мы нашли совпадение в файле (значит ранее уже включили этот файл), то просто выйти
                return True
        f.close

    f = open(local_stackfile, 'a')
    f.write(localpath + "\n")
    f.close
    return True


def append_files(files):
    """Добавить пачку файлов из массива files.

    Это обертка для append_file()
    """
    pause = False
    for filename in files:
        print filename + ': ',
        if append_file(filename):
            print 'OK'
        else:
            pause = True
    if pause:
        raw_input()


def upload():
    import glob
    """Преаплоад файлов. Реальный аплоад в upload_ftp()"""

    files = glob.glob(baseStackPath + ".*")
    if not files:
        print 'Download list is empty'
        return False
    # Выводим список файлов для загрузки
    file = files[0]
    host = file[file.index(baseStackPath) + len(baseStackPath) + 1:].replace('|', '/')
    print host + ':'
    for line in open(file):
        print line,

    print
    command = raw_input("Enter: upload, 'c': clear list, ^C: stop > ")

    if command == 'c':
        # Чистим этот список файлов
        os.remove(file)
        return True

    # Выбрать сервер
    if host[0] == '/':
        local_conf = imp.load_source('local_conf', host + '/.upload.conf.py')
        server = local_conf.conf
        server['basedir'] = host
    else:
        server = servers[host]

    # Загружаем файлы на сервак
    if server['protocol'] == 'ssh':
        upload_ssh(file, server, host)
    elif server['protocol'] == 'serialize':
        upload_serialize(file, server, host)
    elif server['protocol'] == 'form':
        upload_form(file, server, host)
    elif server['protocol'] == 'ftp':
        upload_ftp(file, server, host)
    else:
        raise Exception('Unknown upload protocol "%s"' % server['protocol'])
    return True


def upload_ftp(stackfile, server, server_name):
    from ftplib import FTP
    """Поехали аплоадить файлы на сервак по FTP

    stackfile --    Полное имя файла стека
    server --       Элемент из массива servers
    server_name --  Название сервера

    """
    print 'Connecting'
    ftp = FTP(server['host'], server['user'], server['passwd'])
    ftp.cwd(server['rootdir'])

    print 'Uploading'
    for uploadfile in open(stackfile):
        uploadfile = uploadfile.rstrip()
        remotefile0 = uploadfile.replace('\\', '/');
        remotefile = remotefile0 + '~'
        localdir = 'localdir' in server  and server['localdir'] or localhome_dir
        localwww = 'localdir' in server  and '/' or '/www/'
        print uploadfile,
        ftp.storbinary('STOR ' + remotefile, open(localdir + server_name + localwww + uploadfile, 'rb'))
        ftp.rename(remotefile, remotefile0)
        print '... OK'

    ftp.quit()
    os.remove(stackfile)
    print '--- finished ---'


def upload_ssh(stackfile, server, server_name):
    """Поехали аплоадить файлы на сервак по SSH

    stackfile --    Полное имя файла стека
    server --       Элемент из массива servers
    server_name --  Название сервера

    """
    print 'Uploading'
    if 'basedir' in server:
        dir = server['basedir']
    else:
        localdir = 'localdir' in server  and server['localdir'] or localhome_dir
        localwww = 'localdir' in server  and '/' or '/www/'
        dir = localdir + server_name + localwww    # Локальный каталог проекта

    files = []
    for uploadfile in open(stackfile):
        files.append(uploadfile.rstrip())

    # Параметры tar
    tar_params = ['-C "%s"' % dir,
                  '-czf -']
    if 'owner' in server:
        tar_params += ['--owner ' + server['owner']]
    if 'group' in server:
        tar_params += ['--group ' + server['group']]

    # Make commands
    cmd_tar = 'tar ' + ' '.join(tar_params) + ' ' + ' '.join(files)
    cmd_ssh = 'ssh ' + server['user'] + '@' + server['host']
    cmd_untar = 'tar -C "' + server['rootdir'] + '" -xzf -'
    # ... and run them
    os.system(cmd_tar + ' | ' + cmd_ssh + ' ' + cmd_untar)

    os.remove(stackfile)
    print '--- finished ---'


def upload_serialize(stackfile, server, server_name):
    """Поехали аплоадить файлы на сервак аналогично php serialize()

    stackfile --    Полное имя файла стека
    server --       Элемент из массива servers
    server_name --  Название сервера

    """
    print 'Uploading'
    localdir = 'localdir' in server  and server['localdir'] or localhome_dir
    localwww = 'localdir' in server  and '\\' or '\\www\\'
    dir = localdir + server_name + localwww    # Локальный каталог проекта

    files = []
    # Прочитать файлы в files
    for uploadfile in open(stackfile):
        uploadfile = uploadfile.rstrip()
        files += [(uploadfile, file(dir + uploadfile).read())]

    # Составить serialize
    ser = 'a:1:{s:4:"data";a:%d:{' % len(files)
    for filename, filedata in files:
        ser += 's:%d:"%s";s:%d:"%s";' % (len(filename), filename, len(filedata), filedata)
    ser += '}}'

    # Запрос на сервер
    import urllib, urllib2

    values = {'ser':ser}
    data = urllib.urlencode(values)

    req = urllib2.Request(server['url'], data)
    response = urllib2.urlopen(req)
    the_page = response.read().strip()

    if the_page == '':
        print '--- Error!!! ---'
        return

    print the_page
    raw_input()

    os.remove(stackfile)
    print '--- finished ---'


def upload_form(stackfile, server, server_name):
    """Поехали аплоадить файлы на сервак как form upload

    stackfile --    Полное имя файла стека
    server --       Элемент из массива servers
    server_name --  Название сервера

    """
    print 'Uploading'
    localdir = 'localdir' in server  and server['localdir'] or localhome_dir
    localwww = 'localdir' in server  and '\\' or '\\www\\'
    dir = localdir + server_name + localwww    # Локальный каталог проекта

    import random, string, urllib2

    boundary = ''.join(random.sample(string.letters + string.digits, 30))
    data = ''
    # Прочитать файлы и составить из них data
    for uploadfile in open(stackfile):
        uploadfile = uploadfile.rstrip()
        data += '--' + boundary + '\n' + \
            'Content-Disposition: form-data; name="files[]"; filename="' + uploadfile.replace('\\', '|') + '"\n' + \
            'Content-Transfer-Encoding: binary\n' + \
            '\n' + \
            file(dir + uploadfile, 'rb').read() + '\n'
    data += '--' + boundary + '--\n'

    # Запрос на сервер
    req = urllib2.Request(url=server['url'],
                          data=data,
                          headers={'Content-type': 'multipart/form-data, boundary=' + boundary})

    result = urllib2.urlopen(req).read()
    if result == '':
        print '--- Error!!! ---'
        return

    print result
    raw_input()

    os.remove(stackfile)
    print '--- finished ---'

