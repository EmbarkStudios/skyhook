Welcome to SkyHook's documentation!
===================================

SkyHook was created to facilitate communication between DCCs, standalone applications, web browsers and game engines. As of right now, it's working in Houdini, Blender, Maya and Unreal Engine.

.. image:: ../../wiki-images/UE_Logo_Icon_Black.png
    :width: 20%
.. image:: ../../wiki-images/blender_logo.png
    :width: 20%
.. image:: ../../wiki-images/houdinibadge.png
    :width: 20%
.. image:: ../../wiki-images/maya_logo.png
    :width: 20%



It works both with Python 2.7.x and 3.x and you don't need to have the same Python version across programs. For example, you can build a standalone application in Python 3.8.5 and use SkyHook to communicate with Maya's Python 2.7. This makes it much easier to use than something like RPyC where even a minor version difference can stop it from working.

SkyHook consist of 2 parts that can, but don't have to, work together. There's a client and a server. The server is just a very simple HTTP server that takes JSON requests. It parses those requests and tries to call the function that was passed in the request. It returns another JSON dictionary with the result of the outcome of the function.

The client just makes a a POST request to the server with a JSON payload. This is why you can basically use anything that's able to do so as a client. Could be in a language other than Python, or even just webpage or mobile application. In the future this SkyHook should also support `websockets` connections



.. toctree::
   :maxdepth: 3
   :caption: Contents:

   general
   server
   server_functionality
   server_commands
   client
   unreal_engine



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
