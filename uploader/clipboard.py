# coding: utf-8
import os, sys
from os.path import exists


def check_win_clipboard():
    """Windows clipboard
    """
    import win32clipboard as w  # @UnresolvedImport
    import win32con  # @UnresolvedImport

    # Check the clipboard
    w.OpenClipboard()
    try:
        files = w.GetClipboardData(win32con.CF_HDROP)
    except:
        w.CloseClipboard()
        return False
    # Clean & close clipboard
    w.EmptyClipboard()
    w.CloseClipboard()

    # Add out files
    return files


def check_gtk_clipboard():
    """Linux, gnome cliboard
    """
    import pygtk  # @UnresolvedImport
    pygtk.require('2.0')
    import gtk  # @UnresolvedImport

    # Get the clipboard
    clipboard = gtk.clipboard_get()

    # Check the clipboard
    contents = clipboard.wait_for_contents('text/uri-list')
    if contents is None:
        # Try to parse text
        cliptext = clipboard.wait_for_text()
        if cliptext:
            uris = cliptext.split('\n')
        else:
            return False
    else:
        uris = contents.get_uris()

    # Add our files
    files = []
    for file in uris:
        if file:
            file = file.strip()
            if file.startswith('file://'):
                file = file[7:]
            if exists(file):
                files.append(file)

    # Clear clipboard
    if files:
        clipboard.set_text('')
        clipboard.store()

    return files


def check_mac_clipboard():
    """Mac clipboard
    """
    import subprocess

    # Check the clipboard
    p = subprocess.Popen(['pbpaste'], stdout=subprocess.PIPE)
    p.wait()
    files_str = p.stdout.read()

    files = files_str.decode("utf-8").split('\n')
    files = list(filter(lambda x: x != '' and x.startswith('/'), files))

    # Clear clipboard
    if files:
        p = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
        p.stdin.close()
        p.wait()

    return files


def check():
    if sys.platform == 'win32':
        return check_win_clipboard()
    elif sys.platform == 'linux' or sys.platform == 'linux2':
        return check_gtk_clipboard()
    elif sys.platform == 'darwin':
        return check_mac_clipboard()
    else:
        raise Exception('Unsupported os "%s"' % os.name)
