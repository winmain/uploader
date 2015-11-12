# coding: utf-8
import os.path
import json

from conf import Conf


class Stack:
    def __init__(self, file_name):
        self.data = {}
        self.file_name = file_name
        # Load stack data if file exists
        if os.path.exists(file_name):
            f = open(self.file_name, 'r')
            data = json.load(f)
            self.data = {k: set(v) for k, v in data.iteritems()}
            f.close()

    def save(self):
        to_save = {k: sorted(list(v)) for k, v in self.data.iteritems()}
        f = open(self.file_name, 'w')
        json.dump(to_save, f, indent=2)
        f.close()

    def clear_and_save(self):
        self.data = {}
        if os.path.exists(self.file_name):
            os.remove(self.file_name)

    def append(self, conf_path, local_files):
        """Add files to stack

        @param conf_path    Path to config with .upload.conf.py file
        @param local_files  List of files to add
        """
        assert isinstance(local_files, list)
        if conf_path not in self.data:
            self.data[conf_path] = set()
        if os.name == 'nt':
            local_files = [f.replace('\\', '/') for f in local_files]
        self.data[conf_path] |= set(local_files)

    def __bool__(self):
        return bool(self.data)

    __nonzero__ = __bool__

    def print_data(self):
        paths = sorted(self.data.keys())
        for path in paths:
            print(path + ':')
            for local in sorted(self.data[path]):
                print('  ' + local)
            print('')

        if len(paths) > 1:
            for path in paths:
                count = len(self.data[path])
                print('* %s: %d %s' % (path, count, 'file' if count == 1 else 'files'))
            print('')

    def load_confs(self):
        return {path: Conf(path) for path in self.data.iterkeys()}
