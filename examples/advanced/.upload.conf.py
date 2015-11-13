# coding: utf-8
conf = {
    'user': 'root',
    'rootdir': '/',
    'owner': 'root',
    'group': 'root',

    'ssh_args': ['-p', '2222'],  # Custom ssh arguments (this example set custom port 2222)

    'ignore': ['.hg', '.git', '*.pyc', '.upload.conf.py'],  # Override ignore glob masks
    'ignore_add': ['*.ignore'],  # ... or add more ignore glob masks

    # Execs: these files will be executed on server-side after upload. After execution exec files will be removed.
    # For example: after uploading nginx configs you may want to reload nginx server.
    # Don't forget to mark exec files as executable.
    'execs': ['.upload.exec*'],  # Override execs glob masks
    'execs_add': ['my-exec.sh'],  # ... or add more execs glob masks

    # Multiple servers. Servers can override any parameter in conf
    'servers': [{
        'name': 'one',  # Server names written after '@' symbol in file & folder names to limit upload to only specified servers.
        'host': 'one.example.com',
    }, {
        'name': 'two',
        'host': 'two.example.com',
        'rootdir': '/srv',  # Override rootdir for this server
    }]
}
