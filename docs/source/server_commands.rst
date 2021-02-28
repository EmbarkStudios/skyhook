Server commands
================

The SkyHook server comes with a couple of commands that are not executed from a module, but on the server itself. These are described in
``skyhook.constants.ServerCommands``. They always start with "SKY", so don't add any functions with names like this to any module you load into the server.

.. code-block:: python

    class ServerCommands:
        SKY_SHUTDOWN = "SKY_SHUTDOWN"
        SKY_LS  = "SKY_LS"
        SKY_RELOAD_MODULES = "SKY_RELOAD_MODULES"
        SKY_HOTLOAD = "SKY_HOTLOAD"
        SKY_UNLOAD = "SKY_UNLOAD"
        SKY_FUNCTION_HELP = "SKY_FUNCTION_HELP"

* SKY_SHUTDOWN: Shuts down the server
* SKY_LS: Returns a list with all the function names this server can execute
* SKY_RELOAD_MODULES: Remotely reloads the loaded modules
* SKY_HOTLOAD: needs to be called with the ``skyhook.Constants.module`` argument as a list of module names in the ``parameters``, as explained above.
* SKY_UNLOAD: needs to be called with the ``skyhook.Constants.module`` argument as a list of module names in the ``parameters``, these modules will be removed from the server.
* SKY_FUNCTION_HELP: needs to be called with "function_name" argument as string in the ``parameters``, this will return the names of the arguments, packed arguments and packed keywords a function requires.


Their functionality is hardcoded in ``__process_server_command()`` in the ``Server`` class. If you want to add any extra functionality, this is where you do it.