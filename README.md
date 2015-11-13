Uploader
===

Uploader is a tool for easy file uploads primarily via SSH.

## How to use

For example, you have an html project and a server.
You want to deploy or update your project on the server.

Create a config `.upload.conf.py` named in the project workspace directory:

```
#!python
# coding: utf-8
conf = {
  'user_host': 'root@example.com',    # Change this to your server connection string

  'rootdir': '/',                     # Remote host directory.
  'owner': 'root',                    # Files & directory will be saved with this owner & group on remote host.
  'group': 'root',
}
```

Hint: It's and ordinary python file. You a free to use any python code. Only requirement here - you must define `conf` dictionary.

Our example project structure may look like this:
```
project
project/index.html
project/about.html
project/.upload.conf.py
```

To add file or files upload:

run:
```
$ uploader project/index.html
```
-- or --

Copy file `project/index.html` to clipboard (just file, not contents) and run
```
$ uploader
```

You may repeat this action for other files you need to upload.

When you ready to upload, run:
```
$ uploader
```

You should see files to upload and confirmation prompt:
```
/path/to/my/project:
index.html

Enter: upload, 'c': clear list, 'w': watch for changes, ^C: stop >
```

Hit enter to start upload.
SSH may ask you a password every time.
I recommended you setup [key-based SSH login](https://www.digitalocean.com/community/tutorials/how-to-set-up-ssh-keys--2).


## More examples

See [examples](examples)


## Shortcuts to run uploader

If you use GNOME:
```
gnome-terminal -e uploader
```

You can also run uploader like python package:
```
python -m uploader.run
```
