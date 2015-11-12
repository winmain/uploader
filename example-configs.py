# coding: utf-8
# ====================================
# Example config files .upload.conf.py
# ====================================

# -------------------- Minimal config --------------------

# Upload files to root@example.com via ssh to '/' directory with owner & group root:root

conf = {
    'user_host': 'root@example.com',    # Default user & host to upload.

    'rootdir': '/',                     # Remote host directory.
    'owner': 'root',                    # Files & directory will be saved with this owner & group on remote host.
    'group': 'root',
}


# -------------------- Subdirectory with non-root user --------------------

# Upload files to root@example.com via ssh to '/home/user' directory with owner & group user:user

conf = {
    'user_host': 'root@example.com',

    'rootdir': '/home/user',
    'owner': 'user',
    'group': 'user',

    'ignore': ['.hg', '.git', '*.pyc'],     # ignore glob masks
}


# -------------------- Multiple servers --------------------

conf = {
    'user': 'root',
    'rootdir': '/',
    'owner': 'root',
    'group': 'root',

    'servers': [{                       # Servers can override any parameter
        'host': 'one.example.com',
    }, {
        'host': 'two.example.com',
        'rootdir': '/srv',
    }]
}
