# coding: utf-8
import imp
import os.path
import re
from fnmatch import fnmatch


class Conf:
    def __init__(self, conf_path):
        self.path = conf_path
        local_conf = imp.load_source('local_conf', conf_path + '/.upload.conf.py')
        self.conf = conf = local_conf.conf
        assert isinstance(conf, dict)

        self.protocol = conf.get('protocol', 'ssh')
        if self.protocol not in ['ssh', 'ftp']:
            raise ConfError('Unknown upload protocol "%s"' % self.protocol)

        # List glob filters to ignore files
        self.ignore = conf.get('ignore', ['.hg', '.git', '*.pyc'])
        assert isinstance(self.ignore, list)

        if 'servers' in conf and len(conf['servers']) > 0:
            self.servers = []
            for confSrv in conf['servers']:
                srv = conf.copy()
                for key, value in confSrv.iteritems():
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

        self.name = srv.get('name', self.host)
        if self.name and not re.match('[\d\w\-_]+$', self.name):
            raise ConfError('"name" must contains only letters, digits, "-", "_"')

        self.rootdir = srv.get('rootdir')
        if not self.rootdir:
            raise ConfError('"rootdir" must be set')

        self.owner = srv.get('owner')
        self.group = srv.get('group')
        self.ssh_args = srv.get('ssh_args')

    def remote_path(self, sub_path):
        return os.path.normpath(self.rootdir + '/' + sub_path)



class ConfError(Exception):
    def __init__(self, *args, **kwargs):
        super(ConfError, self).__init__(*args, **kwargs)
