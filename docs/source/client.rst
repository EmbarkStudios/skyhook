SkyHook Client
====================
The client uses Python's ``request`` library to send a POST request to the server. The ``Client`` class is built in such a way that it looks practically identical to use with a SkyHook server or Unreal's Web Remote Control. Behind the scenes there's some extra work done to make it all work. So if you're reading this and you use want to use the ``Client`` as is, great! If you want to tinker with the code a bit yourself, be aware that the ``UnrealClient`` needs some TLC :)

Making a client
----------------------

A SkyHook client only needs to be provided with an address (default is 127.0.0.1) and a port (default is 65500) to connect to.

Making a SkyHook ``Client`` object is as simple as:

.. code-block:: python

    import skyhook.client

    client = skyhook.client.Client()

``skyhook.constants.Ports`` holds the ports that are set up to use with host programs by default. You can use this if you don't remember which program uses which port.

.. code-block:: python

    import skyhook.client
    from skyhook.constants import Ports

    client = skyhook.client.Client()
    client.port = Ports.houdini


DCC specific client
---------------------

All DCCs have their own named client you can use to make your life easier.

.. code-block:: python

    import skyhook.client

    client = skyhook.client.BlenderClient()

That way you don't have to worry about which port to use.

All DCC clients are basically the same as the base ``Client`` class they inherit from. Unreal is the only odd man out, more on that further down.

Executing functions on the server
-----------------------------------

You use the ``execute`` function send a command to the server. It takes a ``command`` argument and an optional ``parameters`` argument. The ``command`` can be a string, or an imported module. Eg:

.. code-block:: python

    import skyhook.client
    import skyhook.modules.blender as blender_module

    client = skyhook.client.BlenderClient()
    client.execute("make_cube")
    client.execute(blender_module.export_usd, parameters={"path": "D:/test_file.usda"})

The ``parameters`` always have to be a dictionary and the keys have to match the argument names used in the function. If you want to execute a function on a SkyHook server without having access to the code, you can use the ``SKY_FUNCTION_HELP`` command to see what the arguments or keywords are called. For example, the function ``echo_message`` expects an argument called ``message``:

.. code-block:: python

    import skyhook.client
    from skyhook.constants import ServerCommands, Ports

    client = skyhook.client.Client()
    client.execute(ServerCommands.SKY_FUNCTION_HELP, parameters={"function_name": "echo_message"})

Returns:

.. code-block:: python

    {
         u'Command': u'SKY_FUNCTION_HELP',
         u'ReturnValue': {u'arguments': [u'message'],
                          u'function_name': u'echo_message'},
         u'Success': True,
         u'Time': u'19:15:14'
     }


Adding a module to the server using the client
-----------------------------------

One of the ``ServerCommands`` is ``SKY_HOTLOAD``. You can use this to add functionality to the server from the client.

.. code-block:: python

    import skyhook.client
    import skyhook.modules.maya as maya
    from skyhook import ServerCommands

    maya_client = skyhook.client.MayaClient()
    maya_client.execute(ServerCommands.SKY_HOTLOAD, parameters={"modules": ["embark_tools.Core.maya_utils"], "is_skyhook_module": False})

This will bring in all the functions from those modules.
