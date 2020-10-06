# coding: utf-8
import imp
import os.path
import re
import json
from fnmatch import fnmatch


class ConfError(Exception):
    def __init__(self, *args, **kwargs):
        super(ConfError, self).__init__(*args, **kwargs)


class Conf:
    def __init__(self, conf_path):
        self.path = conf_path
        local_conf = imp.load_source('local_conf', conf_path + '/.upload.conf.py')
        self.conf = conf = local_conf.conf
        assert isinstance(conf, dict)

        self.protocol = conf.get('protocol', 'ssh')
        if self.protocol not in ['ssh', 'ftp']:
            raise ConfError('Unknown upload protocol "%s"' % self.protocol)

        # Glob filters to ignore files
        self.ignore = conf.get('ignore', ['.hg', '.git', '*.pyc', '.upload.conf.py']) + conf.get('ignore_add', [])
        assert isinstance(self.ignore, list)

        # Exec filters to execute on server side & delete after it
        self.execs = conf.get('execs', ['.upload.exec*']) + conf.get('execs_add', [])
        assert isinstance(self.execs, list)

        if 'servers' in conf and len(conf['servers']) > 0:
            self.servers = []
            for confSrv in conf['servers']:
                srv = conf.copy()
                for key, value in confSrv.items():
                    if value is None:
                        del srv[key]
                    else:
                        srv[key] = value
                self.servers.append(Server(srv))
        else:
            self.servers = [Server(conf)]

    def local_path(self, sub_path):
        return os.path.join(self.path, sub_path)

    def is_ignore(self, filename):
        for pattern in self.ignore:
            if fnmatch(filename, pattern):
                return True
        return False

    def is_exec(self, filename):
        for pattern in self.execs:
            if fnmatch(filename, pattern):
                return True
        return False


class Server:
    def __init__(self, srv):
        assert isinstance(srv, dict)
        self.srv = srv
        self.user_host = srv.get('user_host')
        if self.user_host:
            self.user, self.host = self.user_host.split('@')
        else:
            self.host = srv.get('host')
            self.user = srv.get('user')
            self.user_host = self.user + '@' + self.host

        if not self.host:
            raise ConfError('"host" or "user_host" must be set for conf or server')
        if not self.user:
            raise ConfError('"user" or "user_host" must be set')

        self.name = srv.get('name')
        if self.name and not re.match('[\d\w\-_\.]+$', self.name):
            raise ConfError('"name" must contains only letters, digits, "-", "_", "."')

        self.rootdir = srv.get('rootdir')
        if not self.rootdir:
            raise ConfError('"rootdir" must be set')

        self.owner = srv.get('owner')
        self.group = srv.get('group')
        self.ssh_args = srv.get('ssh_args', None)
        if self.ssh_args is not None and not isinstance(self.ssh_args, list):
            raise ConfError('"ssh_args" must be list')

    def remote_path(self, pure_path):
        return os.path.normpath('/' + pure_path if self.rootdir == '/' else self.rootdir + '/' + pure_path)


class ServerFilter:
    def __init__(self, filter):
        if isinstance(filter, list):
            filter = set(str(v) for v in filter)
        self.filter = filter

    def __and__(self, other):
        if self.filter == 'all' or other.filter is None:
            return other
        elif self.filter is None or other.filter == 'all':
            return self
        else:
            return ServerFilter(self.filter & other.filter)

    def __contains__(self, item):
        assert isinstance(item, Server)
        if self.filter == 'all':
            return True
        elif self.filter is None:
            return False
        else:
            return str(item.name) in self.filter

    def to_value(self):
        if isinstance(self.filter, set):
            return sorted(list(self.filter))
        else:
            return self.filter

    def validate(self, conf):
        assert isinstance(conf, Conf)
        if isinstance(self.filter, set):
            for name in self.filter:
                found = False
                for srv in conf.servers:
                    if srv.name == name:
                        found = True
                        break
                if not found:
                    raise ConfError('Server name "' + name + '" not found in conf.servers')


ServerFilter.all = ServerFilter('all')
ServerFilter.none = ServerFilter(None)


class Stack:
    def __init__(self, file_name):
        self.data = {}
        self.file_name = file_name
        # Load stack data if file exists
        if os.path.exists(file_name):
            f = open(self.file_name, 'r')
            data = json.load(f)
            self.data = {conf_path: set([StackItem.from_value(value) for value in path_rows])
                         for conf_path, path_rows in data.items()}
            f.close()

    def save(self):
        to_save = {conf_path: [stack_item.to_value()
                               for stack_item in sorted(list(path_rows_set), key=lambda si: si.sub_path)]
                   for conf_path, path_rows_set in self.data.items()}
        f = open(self.file_name, 'w')
        json.dump(to_save, f, indent=2)
        f.close()

    def clear_and_save(self):
        self.data = {}
        if os.path.exists(self.file_name):
            os.remove(self.file_name)

    def append(self, conf_path, stack_item):
        """Add files to stack

        @param conf_path    Path to config with .upload.conf.py file
        @param stack_item   Appended StackItem
        """
        assert isinstance(stack_item, StackItem)
        if conf_path not in self.data:
            self.data[conf_path] = set()
        self.data[conf_path] |= {stack_item}

    def __bool__(self):
        return bool(self.data)

    __nonzero__ = __bool__

    def print_data(self, confs):
        paths = sorted(self.data.keys())
        for path in paths:
            conf = confs[path]
            assert isinstance(conf, Conf)
            print((path + ':'))
            for item in sorted(self.data[path], key=lambda v: v.sub_path):
                assert isinstance(item, StackItem)
                print((('[exec] ' if conf.is_exec(os.path.basename(item.pure_path)) else '  ') +
                      item.pure_path +
                      ('  srv:' + str(item.server_filter.to_value()) if item.server_filter != ServerFilter.all else '') +
                      ('  opts:' + str(item.opts) if item.opts else '')))
            print('')

        if len(paths) > 1:
            for path in paths:
                count = len(self.data[path])
                print(('* %s: %d %s' % (path, count, 'file' if count == 1 else 'files')))
            print('')

    def load_confs(self):
        return {path: Conf(path) for path in self.data.keys()}


class StackItem:
    re_filename_ending = re.compile('[^@#][@#][^@#][^/]*')
    re_filename_part = re.compile('[@#][^@#]+')

    def __init__(self, sub_path, pure_path, server_filter, opts):
        self.sub_path = sub_path
        self.pure_path = pure_path
        assert isinstance(server_filter, ServerFilter)
        self.server_filter = server_filter
        assert isinstance(opts, list)
        self.opts = opts

    @classmethod
    def from_sub_path(cls, sub_path):
        server_filter = ServerFilter.all
        opts = []  # list of options
        idx = 0
        pure_path = ''
        while True:
            m = cls.re_filename_ending.search(sub_path, idx)
            if not m:
                pure_path += sub_path[idx:]
                break
            i = m.start(0) + 1
            pure_path += sub_path[idx:i]
            for part in cls.re_filename_part.findall(sub_path[i:m.end(0)]):
                if part[0] == '#':
                    opts = part[1:].split(',')
                elif part[0] == '@':
                    server_filter = server_filter & ServerFilter(part[1:].split(','))
            idx = m.end(0)

        pure_path = pure_path.replace('@@', '@').replace('##', '#')  # purified filename
        return StackItem(sub_path, pure_path, server_filter, opts)

    def __hash__(self):
        return hash(self.sub_path)

    def __eq__(self, other):
        if isinstance(other, StackItem):
            return self.sub_path == other.sub_path
        else:
            return False

    def to_value(self):
        return self.sub_path

    @classmethod
    def from_value(cls, value):
        return cls.from_sub_path(value)
