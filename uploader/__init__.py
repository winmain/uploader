# coding=utf-8
import os
import tempfile
import time

from .structure import *

stackPath = tempfile.gettempdir() + '/.uploader.stack'


def split_conf_path(abspath):
    """Split absolute path to tuple (conf_path, sub_path), where
    conf_path - path to config directory containing .upload.conf.py
    sub_path - path relative to conf_path
    Returns False on fail.
    """
    # Try to file .upload.conf.py file
    if os.path.isdir(abspath) and os.path.exists(abspath + '/.upload.conf.py'):
        path = abspath[:-1] if abspath.endswith('/') else abspath
        return path, '/'
    else:
        path = abspath
        while path != '/':
            path = os.path.dirname(path)
            if os.path.exists(path + '/.upload.conf.py'):
                return path, abspath[len(path) + 1:]
        return False


def append_file(stack, confs, abs_path):
    """Simple add file to stack

    @param stack        Stack to add a file
    @param confs        Dict of Conf as values and conf_path as keys. Filled dynamically
    @param abs_path     Absolute path to file or directory to add
    """
    assert isinstance(stack, Stack)
    conf_and_path = split_conf_path(abs_path)
    if not conf_and_path:
        raise ConfError('Config file .upload.conf.py not found in this directory or parent tree')
    conf_path, sub_path = conf_and_path

    if conf_path not in confs:
        confs[conf_path] = Conf(conf_path)
    conf = confs[conf_path]
    assert isinstance(conf, Conf)

    stack_item = StackItem.from_sub_path(sub_path)
    basename = os.path.basename(stack_item.pure_path)
    if conf.is_ignore(basename):
        return False
    stack_item.server_filter.validate(conf)

    if not os.path.exists(abs_path) and not os.path.islink(abs_path):  # We allow to add broken symlinks
        raise ConfError('File ' + abs_path + ' does not exist')

    if conf.is_exec(basename) and not os.access(abs_path, os.X_OK):
        raise ConfError('Exec ' + abs_path + ' not executable')

    # Recurse into directory
    if os.path.isdir(abs_path):
        for sub_path in os.listdir(abs_path):
            append_file(stack, confs, abs_path + '/' + sub_path)
    else:
        stack.append(conf_path, stack_item)
    return True


def append_files(files):
    """Add multiple files to uploader and save stack.
    This is a wrapper for append_file()
    """
    assert isinstance(files, list)
    stack = Stack(stackPath)
    confs = {}
    for filename in files:
        print(filename + ': ', end=' ')
        if append_file(stack, confs, os.path.abspath(filename)):
            print('OK')
        else:
            print('ignored')
    stack.save()


def receive_command():
    """Wait and process user command."""

    stack = Stack(stackPath)
    if not stack:
        print('Download stack is empty')
        return False
    # Load configs
    confs = stack.load_confs()

    # Print files to upload
    stack.print_data(confs)

    command = input("Enter: upload, 'c': clear list, 'w': watch for changes, ^C: stop > ")

    if command == 'c':
        # Clear upload list
        stack.clear_and_save()
        return True

    if command == 'w':
        # Monitor files & upload them on change
        watch_command(stack, confs)
        return True

    # Upload files to server/servers in parallel threads
    was_error = [False]
    def safe_run(fn):
        try:
            fn()
        except:
            # Print exception stacktrace and mark upload as erroneous.
            was_error[0] = True
            import traceback
            traceback.print_exc()

    import threading
    threads = []
    for conf_path, stack_items in stack.data.items():
        conf = confs[conf_path]
        assert isinstance(conf, Conf)
        for server in conf.servers:
            assert isinstance(server, Server)
            items = [v for v in stack_items if server in v.server_filter]

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
    """Do upload files to server via SSH

    @param conf             Conf - upload config
    @param server           Server to upload
    @param stack_items      List of StackItem for upload
    """
    import io
    import tarfile
    import subprocess
    assert isinstance(conf, Conf)
    assert isinstance(server, Server)

    ssh_args = ['/usr/bin/ssh']
    if server.ssh_args:
        ssh_args += server.ssh_args
    ssh_args += [server.user_host, 'tar', '-C', server.rootdir, '-xzf', '-']

    # Check for execs and add them to ssh_args
    execs = []
    for stack_item in stack_items:
        if conf.is_exec(os.path.basename(stack_item.pure_path)):
            path = server.remote_path(stack_item.pure_path)
            execs += [';', path, ';', 'rm ' + path]
    if execs:
        execs[0] = '&&'
        ssh_args += execs

    if execs:
        print('Uploading as ' + server.user_host + ' and executing ' + ' '.join(execs))
    else:
        print('Uploading as ' + server.user_host)

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
    ret_code = ssh_process.wait()
    if ret_code != 0:
        input()

    print('--- finished ' + server.user_host + ' ---')


def upload_ftp(conf, server, stack_items):
    """Do upload files to server via FTP
    WARNING: not supported. May not work properly.

    @param conf             Conf - upload config
    @param server           Server to upload
    @param stack_items      List of StackItem for upload
    """
    assert isinstance(conf, Conf)
    assert isinstance(server, Server)
    from ftplib import FTP
    print('Connecting')
    ftp = FTP(server.host, server.user, server.srv['passwd'])
    ftp.cwd(server.rootdir)

    print('Uploading')
    for item in stack_items:
        assert isinstance(item, StackItem)
        sub_path = server.remote_path(item.pure_path)
        sub_path_tmp = sub_path + '~'
        print(sub_path, end=' ')
        ftp.storbinary('STOR ' + sub_path_tmp, open(conf.local_path(item.sub_path), 'rb'))
        ftp.rename(sub_path_tmp, sub_path)
        print('... OK')

    ftp.quit()
    print('--- finished ---')


def watch_command(stack, confs):
    """Watch on file(s) change and upload them on change.
    Use Ctrl+c to exit from this mode.

    TODO: conf.owner, conf.group not supported.

    @param stack    Stack with files
    @param confs    Dict of Conf as values and conf_path as keys
    """
    from os.path import getmtime

    def upload(conf, item):
        assert isinstance(item, StackItem)
        for server in conf.servers:
            assert isinstance(server, Server)
            if server in item.server_filter:
                cmd_ssh = ('scp ' + conf.local_path(item.sub_path) + ' ' +
                           server.user_host + ':' + server.remote_path(item.pure_path))
                os.system(cmd_ssh)

    for conf in confs.values():
        assert isinstance(conf, Conf)
        if conf.protocol != 'ssh':
            raise Exception("server protocol must be ssh")

    files = []
    for conf_path, stack_items in stack.data.items():
        conf = confs[conf_path]
        assert isinstance(conf, Conf)
        for item in stack_items:
            assert isinstance(item, StackItem)
            files.append((conf, item, getmtime(conf.local_path(item.sub_path))))
            upload(conf, item)

    print('Watching for changes')

    while True:
        uploaded = False
        for idx, (conf, item, mtime) in enumerate(files):
            assert isinstance(item, StackItem)
            local_path = conf.local_path(item.sub_path)
            new_mtime = getmtime(local_path)
            if new_mtime != mtime:
                print(local_path)
                # Make commands
                upload(conf, item)

                files[idx] = (conf, item, new_mtime)
                uploaded = True

        if not uploaded:
            time.sleep(1)
