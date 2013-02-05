#!/usr/bin/python
# coding: utf-8
import sys
import uploader.clipboard

def main():
    try:
        if len(sys.argv)<2:
            files = uploader.clipboard.check()      # Сначала проверим буфер обмена
        else:
            files = sys.argv[1:]                    # Добавляем все файлы из командной строки

        if files:
            uploader.append_files(files)
        else:
            if not uploader.receive_command():           # Потом проверим, не пуст ли список загрузок
                raw_input()                     # Если он пуст, то тупо ничего не делаем :)

    except KeyboardInterrupt:
        # User pressed CTRL+C, do nothing
        pass

    except:
        # Код ниже стопорит скрипт, если случилась ошибка. Чтоб можно было посмотреть что там такое.
        import atexit
        atexit.register(raw_input)
        print "Unexpected error:", sys.exc_info()[0]
        raise


if __name__ == '__main__':
    main()
