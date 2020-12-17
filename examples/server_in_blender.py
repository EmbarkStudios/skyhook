# Clear the default system console
print("\n" * 60)

import bpy

import sys
import subprocess
import pkg_resources

import traceback

# Blender needs these packages to run skyhook
required = {"PySide2", "requests", "git+https://github.com/EmbarkStudios/skyhook"}

# Let's fine the missing packages
installed = {pkg.key for pkg in pkg_resources.working_set}
missing = required - installed

# and if there are any, pip install them
if missing:
    python = sys.executable
    subprocess.check_call([python, "-m", "pip", "install", *missing], stdout=subprocess.DEVNULL)

try:
    from PySide2.QtCore import *
    from PySide2.QtWidgets import *
    from PySide2.QtGui import *
except Exception:
    print("Couldn't install PySide2")

class SkyhookServer():
    def __init__(self):
        self.thread, self.executor, self.server = \
            server.start_executor_server_in_thread(host_program=HostPrograms.blender,
                                                   load_modules=[blender])
        self.__app = QApplication.instance()
        if not self.__app:
            self.__app = QApplication(["blender"])
        if self.__app:
            self.__app.processEvents()

if __name__ == "__main__":
    try:
        import skyhook
        from skyhook import HostPrograms
        from skyhook.modules import blender
        from skyhook import server

        bpy.types.Scene.skyhook_server = SkyhookServer()

    except Exception as err:
        print(str(traceback.format_exc()))
        print(str(err))
