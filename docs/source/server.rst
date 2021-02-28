SkyHook Server
===============

The server is built on Python's ``wsgiref.simple_server`` and PyQt5/PySide2. Once it's started, it enters an infinite loop where it continues to take requests until its ``__keep_running`` boolean is set to False.
Depending on where you're using the server, you might use different ways to start it. Also, every host program has its own predefined port to which the server binds itself. This can be overridden if you want (``Server.port``) This could potentially be useful if you have both a GUI and a headless version of a program running.


Maya and Houdini
-----------------

Maya and Houdini will happily execute any Python code in a different thread without any (added) stability issues (please link to this page when you prove me wrong :)). As such, we can launch the server by making a SkyHook server object, making a QThread object, linking the two together and starting the ``run`` function on the thread:

.. code-block:: python

    from skyhook.server import Server
    skyhook_server = Server(host_program="maya", load_modules=["maya"])
    thread_object = QThread()
    skyhook_server.is_terminated.connect(partial(__kill_thread, thread_object))
    skyhook_server.moveToThread(thread_object)

    thread_object.started.connect(skyhook_server.start_listening)
    thread_object.start()

Or, you can use the ``start_server_in_thread`` function from ``skyhook.server``:

.. code-block:: python

    import skyhook.server as shs
    from skyhook.constants import HostPrograms
    thread, server = shs.start_server_in_thread(host_program=HostPrograms.houdini, load_modules=["houdini"])

It returns the ``QThread`` and the ``Server`` object.

Blender
--------------
Blender is a bit finicky when it comes to executing anything from ``bpy.ops`` in a thread different than the main program thread. Because of this, we have to make an object that gets instructions from the SkyHook server whenever the server handles a request. This object is called a ``MainThreadExecutor`` and lives in the ``skyhook.server`` module. While the SkyHook server runs in a separate thread, the ``MainThreadExecutor`` (as the name suggests) runs in Blender's main thread. We pass information from the server to the main thread so it can safely be executed there.

Adding functionality to the ``blender`` module also needs some extra care.

You can run construct the server like this:

.. code-block:: python

    import skyhook.server as shs
    from skyhook.constants import HostPrograms

    skyhook_server = Server(host_program=HostPrograms.blender, load_modules=["blender"], use_main_thread_executor=True)
    executor = MainThreadExecutor(skyhook_server)
    skyhook_server.exec_command_signal.connect(executor.execute)

    thread_object = QThread()
    skyhook_server.moveToThread(thread_object)
    thread_object.started.connect(skyhook_server.start_listening)
    thread_object.start()

Or, use this one-liner:

.. code-block:: python

    import skyhook.server as shs
    from skyhook.constants import HostPrograms
    thread, executor, server = shs.start_executor_server_in_thread(host_program=HostPrograms.blender, load_modules=["blender"])

Blender as a whole is a bit weirder when it comes to running a Qt Application and needs some boiler plate code to do so. I found that the following code is able to run the server without much problems:

.. code-block:: python

    # Clear the default system console
    print("\n" * 60)

    import bpy

    import sys
    import subprocess
    import pkg_resources

    import traceback

    # Blender needs these packages to run skyhook
    required = {"PySide2", "requests", "git+https://github.com/EmbarkStudios/skyhook"}

    # Let's find the missing packages
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


Standalone
--------------

SkyHook doesn't necessarily need to run inside a host program. It can be a stand alone application as well that you can dump on machine somewhere to control. In this case, you'll most likely won't have to worry about running it in a separate thread. You can start it like this, just from a Python prompt:

.. code-block:: python

    import skyhook.server as shs
    from skyhook.constants import HostPrograms

    skyhook_server = Server()
    skyhook_server.start_listening()

Since we're not supplying it with a host program, it will bind itself to ``skyhook.constants.Ports.undefined`` (65500). Unless you add the ``load_modules`` argument when you make the ``Server``, the functionality will come from ``skyhook.modules.core``.

The one-liner:

.. code-block:: python

    import skyhook.server as shs
    shs.start_blocking_server()


I'm actually using it to connect to a Raspberry Pi that controls my Christmas lights 😄 🎄

