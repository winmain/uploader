#!/usr/bin/python
# coding: utf-8
import sys
import uploader

if __name__ == '__main__':
    try:
        if len(sys.argv)<2:
            if not uploader.check_clipboard():      # Сначала проверим буфер обмена
                if not uploader.upload():           # Потом проверим, не пуст ли список загрузок
                    raw_input()                     # Если он пуст, то тупо ничего не делаем :)
        else:
            uploader.append_files(sys.argv[1:])     # Добавляем все файлы из коммандной строки

    except KeyboardInterrupt:
        # User pressed CTRL+C, do nothing
        pass

    except:
        # Код ниже стопорит скрипт, если случилась ошибка. Чтоб можно было посмотреть что там такое.
        import atexit
        atexit.register(raw_input)
        print "Unexpected error:", sys.exc_info()[0]
        raise
