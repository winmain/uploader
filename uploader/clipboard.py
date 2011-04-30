# coding: utf-8
import os
from os.path import exists

def check_win_clipboard():
    """Windows: Проверим-ка мы буфер обмена. Можно копировать файлы и заносить их в список.
    """
    import win32clipboard as w #@UnresolvedImport
    import win32con #@UnresolvedImport

    # Смотрим, что у нас в буфере
    w.OpenClipboard()
    try:
        files = w.GetClipboardData(win32con.CF_HDROP)
    except:
        w.CloseClipboard()
        return False
    # Очищаем и закрываем буфер
    w.EmptyClipboard()
    w.CloseClipboard()

    # Добавляем наши файлы
    return files


def check_gtk_clipboard():
    """Linux, gnome: Проверим-ка мы буфер обмена. Можно копировать файлы и заносить их в список.
    """
    import pygtk #@UnresolvedImport
    pygtk.require('2.0')
    import gtk #@UnresolvedImport

    # get the clipboard
    clipboard = gtk.clipboard_get()

    # Смотрим, что у нас в буфере
    contents = clipboard.wait_for_contents('text/uri-list')
    if contents is None:
        # Попробовать разобрать текст
        cliptext = clipboard.wait_for_text()
        if cliptext:
            uris = cliptext.split('\n')
        else:
            return False
    else:
        uris = contents.get_uris()

    # Добавляем наши файлы
    files = []
    for file in uris:
        if file:
            file = file.strip()
            if file.startswith('file://'):
                file = file[7:]
            if exists(file):
                files.append(file)

    # Очищаем буфер
    if files:
        clipboard.set_text('')
        clipboard.store()

    return files


def check():
    if os.name == 'nt':
        return check_win_clipboard()
    elif os.name == 'posix':
        return check_gtk_clipboard()
    else:
        raise Exception('Unsupported os "%s"' % os.name)

