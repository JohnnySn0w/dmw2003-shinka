"""Run a build in its own hidden UTF-8 console, including CMake batch files.

The launcher creates this process with CREATE_NEW_CONSOLE and SW_HIDE. Code-page
changes affect only that private console, never the user's terminal or system.
"""
import ctypes
import os
import subprocess
import sys


def main():
    if len(sys.argv) < 2:
        raise ValueError('A build command is required.')
    if os.name == 'nt':
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        if not kernel.SetConsoleCP(65001) or not kernel.SetConsoleOutputCP(65001):
            raise ctypes.WinError(ctypes.get_last_error())
    return subprocess.call(sys.argv[1:])


if __name__ == '__main__':
    sys.exit(main())
