# -*- coding: utf-8 -*-

name = 'skyhook'

version = '0.1.0'

requires = [
    "platform-windows",
    "arch-AMD64",
]


build_command = "python {root}/package.py {install}"

def commands():
    import os
    # Path to cmake.exe and cmake-gui.exe
    env.PYTHONPATH.append(os.path.join("{root}", "python"))


def build(*args):
    import os
    import shutil

    # build config
    is_build    = os.getenv("REZ_BUILD_ENV")
    build_path  = os.getenv("REZ_BUILD_PATH")
    is_install  = os.getenv("REZ_BUILD_INSTALL")
    install_path = os.getenv("REZ_BUILD_INSTALL_PATH")
    source_path = os.getenv("REZ_BUILD_SOURCE_PATH")
    is_install  = os.getenv("REZ_BUILD_INSTALL")

    if is_install:
        import glob
        src = os.path.join(source_path, "skyhook")
        dest = os.path.join(install_path, "python", "skyhook")
        shutil.rmtree(dest, ignore_errors=True)
        shutil.copytree(src, dest, dirs_exist_ok=True)


if __name__ == "__main__":  
    import sys
    build(*sys.argv)
