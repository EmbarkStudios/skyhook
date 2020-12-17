print("\n" * 30)

import bpy

import sys
import subprocess
import pkg_resources

import traceback

required = {"PySide2"}
installed = {pkg.key for pkg in pkg_resources.working_set}
missing = required - installed

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
        self._app = QApplication.instance()
        if not self._app:
            self._app = QApplication(["blender"])
        if self._app:
            self._app.processEvents()

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
