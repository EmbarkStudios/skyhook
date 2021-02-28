Server functionality
=====================


The server itself doesn't really do much. Any functionality needs to come from a SkyHook module that either gets loaded when the server is started or hotloaded when the server is running. Modules should be split between different host programs and should ideally be placed in the ``skyhook.modules`` folder.

* You can load these modules either by name (as a ``string``) or as a Python ``module`` object.
* You can load them when constructing the ``Server`` object, hotload them using the ``Server`` object or remotely using the ``SKY_HOTLOAD`` server command.

To load the modules when constructing the server, you just pass a list to the ``load_modules`` argument. The following example shows how to load the ``houdini`` module as a string and the ``maya`` module as a ``module`` object. These can be mixed if you want to.

.. code-block:: python

    import skyhook.server
    # import the maya module to then pass into the load_modules argument
    import skyhook.modules.maya as maya_module
    from skyhook import HostPrograms

    thread, server = skyhook.server.start_server_in_thread(host_program=HostPrograms.houdini, load_modules=["houdini", maya_module])

If you don't want to restart the server and have access to the ``Server`` object, you can invoke the ``hotload_module()`` function to add a module:

.. code-block:: python

    import skyhook.server
    import skyhook.modules.maya as maya_module
    from skyhook import HostPrograms

    thread, server = skyhook.server.start_server_in_thread(host_program=HostPrograms.houdini)
    # server is running, now hotload some modules
    server.hotload_module("houdini")
    server.hotload_module(maya_module)


If you don't have access to the ``Server`` object, you can also use the server command ``SKY_HOTLOAD`` to remotely tell the server to add a new module. An example coud look like this:

.. code-block:: python

    import skyhook.client
    from skyhook import ServerCommands

    maya_client = skyhook.client.MayaClient()
    maya_client.execute(ServerCommands.SKY_HOTLOAD, parameters={"modules": ["maya"]})


Adding functionality to SkyHook from elsewhere
-------------------------------------------------
The examples above all assume that whatever module you want to load is located in the ``skyhook.modules`` folder. It is possible to load modules from elsewhere if you so fancy. This is done using by setting the ``is_skyhook_module`` to ``False`` in the ``hotload_module()`` function on ``Server``.

Example:

.. code-block:: python

    import skyhook.server
    import skyhook.modules.maya as maya_module
    import embark_tools.Core.houdini_utils as houdini_utils
    from skyhooks import HostPrograms

    thread, server = skyhook.server.start_server_in_thread(host_program=HostPrograms.houdini)
    server.hotload_module("embark_tools.Core.maya_utils", is_skyhook_module=False)
    server.hotload_module(houdini_utils, is_skyhook_module=False)


.. warning::

    Anything sent to the server remotely is in JSON form. Meaning that if it can't be serialized, the SkyHook server won't know what to do with it. So doing something like this will fail:

.. code-block:: python

    import skyhook.client
    import skyhook.modules.maya as maya_module
    from skyhookimport ServerCommands

    maya_client = skyhook.client.MayaClient()
    # send the module as a Python module instead of a string
    maya_client.execute(ServerCommands.SKY_HOTLOAD, parameters={"modules": [maya_module], "is_skyhook_module": False})


Function naming clashes
------------------------

By default, the server will look through all its loaded modules to find the function that's being called by the client. This means that if you have modules that both have a function with the same name, the server might execute the function from the wrong module. You can set ``module_name`` in the function ``get_function_by_name`` to specify a specific module to search in. If you want to search in a SkyHook module, just passing the name of the module will work. However, if you've loaded a module from outside SkyHook, you have to provide the complete module path.

You set this module name, or module path, by adding ``skyhook.constants.Constands.module`` ("_Module") to the parameters of your request.

.. note::

    This might not be working correctly 100% of the time. For now, it might be best to avoid having the same function name in different modules. You're a creative person, think of a better, COOLER function name than the one that already exists!