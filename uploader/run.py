#!/usr/bin/env python3
# coding: utf-8
import sys

from uploader import ConfError
import uploader.clipboard


def main():
    try:
        if len(sys.argv) < 2:
            files = uploader.clipboard.check()      # Check clipboard
        else:
            files = sys.argv[1:]                    # Add files from commandline

        if files:
            uploader.append_files(files)
        else:
            if not uploader.receive_command():  # Process command
                input()

    except KeyboardInterrupt:
        # User pressed CTRL+C, do nothing
        pass

    except ConfError as e:
        print()
        print("Error:", str(e))
        input()

    except:
        # Code below stops the script on error to view a problem.
        import atexit
        atexit.register(input)
        print("Unexpected error:", sys.exc_info()[0])
        raise


if __name__ == '__main__':
    main()
