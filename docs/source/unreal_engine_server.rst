SkyHook server in Unreal
=========================

.. warning::
    Only supporting Unreal Engine 4.26 and up!


Unreal is a bit of a different beast. It does support Python for editor related tasks, but seems to be starving any threads pretty quickly. That's why it's pretty much impossible to run the SkyHook server in Unreal like we're able to do so in other programs. However, as explained in the main outline, SkyHook clients don't have to necessarily connect to SkyHook servers. That's why we can use ``skyhook.client.UnrealClient``  with Unreal Engine's built-in Web Remote Control.

Web Remote Control is a plugin you have first have to load before you can use it. It's still very much in beta right now and changing any functionality is not easy. After you've loaded the plugin, start it by typing ``WebControl.StartServer`` in the default ``Cmd`` console in the Output Log window. Or, if you want to always start with the project, enter ``WebControl.EnableServerOnStartup 1``.

Loading a SkyHook module in Unreal is done by just importing it like normal. Assuming the code for the SkyHook module is in a file called "skyhook" in the Python folder (/Game/Content/Python), you can just do:

.. code-block:: python

    import skyhook


The SkyHook Unreal module
--------------------------

Unreal has specific requirements to run Python code. So you have to keep that in mind when adding functionality to the SkyHook module. In order for it to be "seen" in Unreal you need to decorate your class and functions with specific Unreal decorators.

Decorating the class with ``unreal.uclass()``:

.. code-block:: python

    import unreal

    @unreal.uclass()
    class SkyHookCommands(unreal.BlueprintFunctionLibrary):
        pass


Epic recommends marking all your functions as ``static``:

.. code-block:: python

    @unreal.ufunction(static=True)
    def say_hello():
        unreal.log_warning("Hello!")



If you want your function to accept parameters, you need to add them in the decorator like this

.. code-block:: python

    import os

    @unreal.ufunction(params=[str, str], static=True)
    def rename_asset(asset_path, new_name):
        dirname = os.path.dirname(asset_path)
        new_name = dirname + "/" + new_name
        unreal.EditorAssetLibrary.rename_asset(asset_path, new_name)
        unreal.log_warning("Renamed to %s" % new_name)


.. note::
    You can not use Python's ``list`` in the decorator for the Unreal functions. Use ``unreal.Array(type)``, eg: ``unreal.Array(float)``.

.. note::
    You can not use Python's ``dict`` in the decorator for the Unreal functions. Use ``unreal.Map(key type, value type)``, eg: ``unreal.Map(str, int)``

Add the return type in your decorator like this:

.. code-block:: python

    @unreal.ufunction(params=[int], ret=unreal.Map(str, int), static=True)
    def get_dictionary(health_multiplier):
        return_dict = {
            "health": 20 * health_multiplier,
            "damage": 90
        }

        return return_dict


Returning segues us into a couple of things to keep in mind.



Things to keep in mind
----------------------

.. warning::
    In 4.26 and 4.26.1 there's a bug that causes your editor to crash if you're returning a non-empty ``unreal.Array``` over Web Remote Control from Python. It's been reported and hopefully will get fixed soon. This is an example function that will crash UE.

.. code-block:: python

    @unreal.ufunction(ret=unreal.Array(float), static=True)
    def get_list_float():
        return_list = [1.2, 55.9, 65.32]
        return return_list

A way to get around this is to return a string version of the list, instead of the actual list. Since the return object that's being sent back to the client needs to be a JSON, you can't be returning any "exotic" objects in a list anyway.

This function WON'T crash your editor:

.. code-block:: python

    @unreal.ufunction(ret=str, static=True)
    def get_list_float():
        return_list = [1.2, 55.9, 65.32]

        #stringify it!
        return str(return_list)

When the return value is sent back to the client, the client will first try to ``eval`` it to see if it contains a Python object. This happens in ``skyhook.client.UnrealClient.execute```. While this was initially added as a bit of a hack to just get it working, it actually soon became useful in another way.

Consider the following function. We want to return a dictionary where the values are lists of integers:

.. code-block:: python

    @unreal.ufunction(ret=unreal.Map(str, int), static=True)
    def get_dictionary_with_lists():
        return_dict = {
            "checkpoints": [4, 18, 25],
            "num_enemies": [3, 9, 12]
        }

        return return_dict

Unreal will throw the following error:

.. warning::

    `TypeError: Map: 'value' (Array (IntProperty)) cannot be a container element type (directly nested containers are not supported - consider using an intermediary struct instead)`

However, when the ``return_dict`` is first turned into a string before returning it (be sure to also set your return type to string, ``ret=str``) everything works just fine. Your client on the receiving end will turn it into a Python `dict` again.
