# 🌴 SkyHook

[![Embark](https://img.shields.io/badge/embark-open%20source-blueviolet.svg)](https://embark.dev)

## Engine and DCC communication system

SkyHook was created to facilitate communication between DCCs, standalone applications, web browsers and game engines. As of right now, it’s working in Houdini, Blender, Maya, Substance Painter and Unreal Engine.

<table style="width: 100%">
  <tr>
    <td><img src="./wiki-images/blender_logo.png" height="50" /></td>
    <td><img src="./wiki-images/houdinibadge.jpg" height="50" /></td>
    <td><img src="./wiki-images/UE_Logo_Icon_Black.png" height="50" /></td>
    <td><img src="./wiki-images/maya_logo.png" height="50" /></td>
    <td><img src="./wiki-images/substance_painter.png" height="50" /></td>
  </tr>
 </table>

The current mainline version is for Python 3.6 and up. 

SkyHook consist of 2 parts that can, but don’t have to, work together. There’s a client and a server. The server is just a very simple HTTP server that takes JSON requests. It parses those requests and tries to execute what was in them. The client just makes a a POST request to the server with a JSON payload. This is why you can basically use anything that’s able to do so as a client. Could be in a language other than Python, or even just webpage or mobile application.

## Pip installing

You should be able to pip install this package like this:
```batch
pip install --upgrade git+https://github.com/EmbarkStudios/skyhook
```

# Quick Start

Some quick start examples to help you get on your way. 

## Maya
Let's say you have a file called `skyhook_commands.py` that is available in `sys.path` inside of Maya. The following are some example functions you could have:

`skyhook_commands.py`

```python
import os
import maya.cmds as cmds
import pymel.core as pm

def delete_namespace(namespace, nuke_all_contents=False):
    """
    Removes all objects from the given namespace and then removes it.
    If given the nuke flag, will delete all objects from the namespace too.

    :param namespace: *string*
    :param nuke_all_contents: *bool* whether to also delete all objects contained in namespace and their children
    :return:
    """
    try:
        if nuke_all_contents is not True:
            pm.namespace(force=True, rm=namespace, mergeNamespaceWithRoot=True)
            pm.namespace (set=':')
        else:
            nmspc_children = cmds.namespaceInfo(namespace, listOnlyNamespaces=True, recurse=True)
            if nmspc_children:
                # negative element count to get them sorted from deepest to shallowest branch.
                sorted_name_list = sorted(nmspc_children, key=lambda element: -element.count(":"))
                for obj in sorted_name_list:
                    cmds.namespace(removeNamespace=obj, deleteNamespaceContent=True)
            cmds.namespace(removeNamespace=namespace, deleteNamespaceContent=True)
        return True
    except Exception as err:
        print(err)
        return False

def get_scene_path(full_path=True, name_only=False, folder_only=False, extension=True):
    """
    Extension of the normal pm.sceneName() with a bit more options

    :param full_path: *bool* returns the full path (D:/Game/scenes/enemy.ma)
    :param name_only: *bool* returns the name of the file only (enemy.ma)
    :param folder_only: *bool* returns the folder of the file only (D:/Game/scenes)
    :param extension: *bool* whether or not to return the name with the extension
    :return: *string*
    """
    if name_only:
        name = os.path.basename(pm.sceneName())
        if extension:
            return name
        return os.path.splitext(name)[0]
    if folder_only:
        return os.path.dirname(pm.sceneName())
    if full_path:
        if extension:
            return pm.sceneName()
        return os.path.splitext(pm.sceneName())[0]
    return ""


def selection(as_strings=False, as_pynodes=False, st=False, py=False):
    """
    Convenience function to easily get your selection as a string representation or as pynodes

    :param as_strings: *bool* returns a list of strings
    :param as_pynodes: *bool* returns a list of pynodes
    :param st: *bool* same as as_strings
    :param py: *bool* same as as_pynodes
    :return:
    """
    if as_strings or st:
        return [str(uni) for uni in cmds.ls(selection=True)]

    if as_pynodes or py:
        return pm.selected()


```


Running this code inside Maya sets up a SkyHook server:
```python
import pprint
import skyhook_commands # this is the file listed above
from skyhook import server as shs
from skyhook.constants import ServerEvents, HostPrograms

def catch_execution_signal(command, parameters):
    """
    This function is ran any time the skyhook server executes a command. You can use this as a callback to do 
    specific things, if needed. 
    """
    print(f"I just ran the command {command}")
    print("These were the parameters of the command:")
    pprint.pprint(parameters)
    
    if command == "SKY_SHUTDOWN":
        print("The shutdown command has been sent and this server will stop accepting requests")
    elif command == "get_from_list":
        print("Getting this from a list!")


# Since we're running this in Maya, we want to make use of a MainThreadExecutor, so that Maya's code gets executed in the
# main (UI) thread. Otherwise Maya can get unstable and crash depending on what it is we're doing. Therefor we'll use the 
# `start_executor_server_in_thread` function, pass along "maya" as a host program so that the proper MainThreadExecutor is
# started. 
thread, executor, server = shs.start_executor_server_in_thread(host_program=HostPrograms.maya)
if server:
    server.hotload_module("maya_mod")  # this gets loaded from the skyhook.modules
    server.hotload_module(skyhook_commands, is_skyhook_module=False)  # passing False to is_skyhook_module, because this files comes from outside the skyhook package

    server = server
    executor = executor
    thread = thread

    server.events.connect(ServerEvents.exec_command, catch_execution_signal) # call the function `catch_execution_signal` any time this server executes a command through its MainThreadExecutor
    server.events.connect(ServerEvents.command, catch_execution_signal) # call the same function any time this server exectures a command outside of its MainThreadExecutor
```

We'll make a `MayaClient` to run any of the functions that we've provided the server with. This can be run as a standalone Python program, or from another piece of software, like Blender or Substance Painter.

```python
from skyhook import client

maya_client = client.MayaClient()

result = maya_client.execute("selection", {"st": True})
print(f"The current selection is: {result.get('ReturnValue', None)}" )
# >> The current selection is: ['actor0:Leg_ctrl.cv[14]', 'actor0:Chest_ctrl', 'actor0:bake:root']

result = maya_client.execute("get_scene_path")
print(f"The current scene path is: {result.get('ReturnValue', '')}")
# >> The current scene path is: D:/THEFINALS/MayaScenes/Weapons/AKM/AKM.ma
```


## SkyHook server in Unreal

Unreal is a bit of a different beast. It does support Python for editor related tasks, but seems to be starving any threads pretty quickly. That's why it's pretty much impossible to run the SkyHook server in Unreal like we're able to do so in other programs. However, as explained in the main outline, SkyHook clients don't have to necessarily connect to SkyHook servers. That's why we can use ``skyhook.client.UnrealClient``  with Unreal Engine's built-in Remote Control API.

Make sure the Remote Control API is loaded from `Edit > Plugins`

![image](https://user-images.githubusercontent.com/7821618/165508115-6d6919bd-49c0-4c15-992f-99c00887ac33.png)

Loading a SkyHook module in Unreal is done by just importing it like normal. Assuming the code for the SkyHook module is in a file called `skyhook_commands` in the Python folder (`/Game/Content/Python`), you can just do:


```python
import skyhook_commands
```

If you want to make sure it's always available when you start the engine, add an `init_unreal.py` file in the Python folder and import the module from there. I've had problems with having a `__pycache__` folder on engine start up, so I just deleted it from that some `init_unreal.py` file:


```python
# making sure skyhook_commands are loaded and ready to go
import skyhook_commands
# adding this here because it's a pain in the ass to retype every time
from importlib import reload

# cleaning up pycache folder
pycache_folder = os.path.join(os.path.dirname(__file__), "__pycache__")
if os.path.isdir(pycache_folder):
    shutil.rmtree(pycache_folder)
```

## The SkyHook Unreal module

Unreal has specific requirements to run Python code. So you have to keep that in mind when adding functionality to the SkyHook module. In order for it to be "seen" in Unreal you need to decorate your class and functions with specific Unreal decorators.

Decorating the class with `unreal.uclass()`:

```python
import unreal

@unreal.uclass()
class SkyHookCommands(unreal.BlueprintFunctionLibrary):
    def __init__(self):
        super(SkyHookCommands, self).__init__()
```

If you want your function to accept parameters, you need to add them in the decorator like this

```python
import unreal
import os

@unreal.ufunction(params=[str, str], static=true)
def rename_asset(asset_path, new_name):
    dirname = os.path.dirname(asset_path)
    new_name = dirname + "/" + new_name
    unreal.EditorAssetLibrary.rename_asset(asset_path, new_name)
    unreal.log_warning("Renamed to %s" % new_name)
```
---
**NOTE**

You can not use Python's `list` in the decorator for the Unreal functions. Use `unreal.Array(type)`, eg: `unreal.Array(float)`.

---

---
**NOTE**

You can not use Python's `dict` in the decorator for the Unreal functions. Use `unreal.Map(key type, value type)`, eg: `unreal.Map(str, int)

---


## Returning values to the SkyHook client

Whenever you want to return anything from Unreal back to your SkyHook client, add the `ret` keyword in the function parameters:
```python
@unreal.ufunction(params=[str], ret=bool, static=True)
def does_asset_exist(asset_path=""):
    """
    Return True or False whether or not asset exists at given path

    :return: *bool*
    """
    return_value = unreal.EditorAssetLibrary.does_asset_exist(asset_path)

    return return_value
```


## Returning "complex" items from Unreal

Let's say you want to return a dictionary from Unreal that looks like this:

```python
my_dict = {
    "player_name": "Nisse",
    "player_health": 98.5,
    "player_lives": 3,
    "is_player_alive": True
}
```

Unfortunately, due to how Unreal works, you can't specify your return value as a dictionary or list with mixed values. This can be quite problematic because sometimes that's exactly what you want. To solve this you can just stringify your return value and it will be decoded into a Python object on the client side. 

So in the example above, you'd do something like

```python
@unreal.ufunction(params=[str], ret=str, static=True)
def my_cool_function(player_name=""):
    my_dict = {
            "player_name": "Nisse",
            "player_health": 98.5,
            "player_lives": 3,
            "is_player_alive": True
    }

    return str(my_dict)
```

Since "this will just work", you can basically always just return a string like that. 


## Complete example of a `skyhook_commands.py` file in Unreal

Here's a short snippet of a skyhook_commands.py to help you get on your way

```python
import unreal

import os
import pathlib

@unreal.uclass()
class SkyHookCommands(unreal.BlueprintFunctionLibrary):
    
    @unreal.ufunction(params=[str], ret=str, static=True)
    def create_control_rig_from_skeletal_mesh(skeletal_mesh_path):
        skeletal_mesh = unreal.EditorAssetLibrary.load_asset(skeletal_mesh_path)
        
        # make the blueprint using a the factory
        ctrl_rig_blueprint: unreal.ControlRigBlueprint = unreal.ControlRigBlueprintFactory.create_control_rig_from_skeletal_mesh_or_skeleton(selected_object=skeletal_mesh)
        
        # chuck in a begin execution node
        controller: unreal.RigVMController = ctrl_rig_blueprint.get_controller_by_name("RigVMModel")
        controller.add_unit_node_from_struct_path(script_struct_path=unreal.RigUnit_BeginExecution.static_struct(),
                                                  position=unreal.Vector2D(0.0, 0.0),
                                                  node_name="RigUnit_BeginExecution")
        
        # return the path of the blueprint we just made
        return ctrl_rig_blueprint.get_path_name()


    @unreal.ufunction(params=[str, str, str, bool, bool, int, bool], ret=bool, static=True)
    def import_animation(source_path, destination_path, unreal_skeleton_path, replace_existing, save_on_import, sample_rate, show_dialog):
        destination_path = match_existing_folder_case(destination_path)

        options = unreal.FbxImportUI()

        options.import_animations = True
        options.skeleton = unreal.load_asset(unreal_skeleton_path)
        options.anim_sequence_import_data.set_editor_property("animation_length", unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        options.anim_sequence_import_data.set_editor_property("remove_redundant_keys", False)
        options.anim_sequence_import_data.set_editor_property("custom_sample_rate", sample_rate)
        unreal.log_warning(f"Imported using sample rate: {sample_rate}")
        # options.anim_sequence_import_data.set_editor_property("use_default_sample_rate", True)

        task = unreal.AssetImportTask()
        task.automated = not show_dialog
        task.destination_path = destination_path
        task.filename = source_path
        task.replace_existing = replace_existing
        task.save = save_on_import
        task.options = options

        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

        return True    

    @unreal.ufunction(params=[str, str, str], ret=str, static=True)
    def create_material_instance(destination_path="", material_name="new_material", parent_path=""):
        """
        Create a material instance at the desetination with the provided name and parent material

        :return: *str* asset path of material instance
        """
        # Get asset tools
        destination_path = match_existing_folder_case(destination_path)
        assetTools = unreal.AssetToolsHelpers.get_asset_tools()

        if unreal.EditorAssetLibrary.does_asset_exist(parent_path):
            parent_material = unreal.load_asset(parent_path)
        else:
            print("Could not find parent material " + parent_path)
            return ""

        material_instance = assetTools.create_asset(asset_name=material_name, package_path=destination_path, asset_class=unreal.MaterialInstanceConstant, factory=unreal.MaterialInstanceConstantFactoryNew())
        unreal.MaterialEditingLibrary().set_material_instance_parent(material_instance, parent_material)

        return material_instance.get_path_name()

    @unreal.ufunction(params=[str], ret=bool, static=True)
    def load_map(filename=""):
        """
        Set the position and rotation of the viewport camera

        :return: *bool* true if the action is completed
        """

        # Get path for currently loaded map
        current_map = unreal.EditorLevelLibrary.get_editor_world().get_path_name()

        # If the requested map is not loaded, prompt before loading
        if filename != current_map:
            if show_dialog_confirm("Skyhook Load Map", "Are you sure you want to load this map? Any changes to the current map will be lost!") == unreal.AppReturnType.YES:
                unreal.EditorLoadingAndSavingUtils.load_map(filename)
            else:
                return False

        return True    

    @unreal.ufunction(params=[str, unreal.Array(str)], ret=bool, static=True)
    def load_map_and_select_actors(filename="", actor_guids=[]):
        """
        Set the position and rotation of the viewport camera

        :return: *bool* true if the action is completed
        """

        # Get path for currently loaded map
        current_map = unreal.EditorLevelLibrary.get_editor_world().get_path_name()

        # If the requested map is not loaded, prompt before loading
        if filename != current_map:
            if show_dialog_confirm("Skyhook Load Map", "Are you sure you want to load this map? Any changes to the current map will be lost!") == unreal.AppReturnType.YES:
                unreal.EditorLoadingAndSavingUtils.load_map(filename)
            else:
                return False

        guids = []

        # Parse guid string to guid struct
        for actor_guid in actor_guids:
            guids.append(unreal.GuidLibrary.parse_string_to_guid(actor_guid)[0])

        # Create actor list (STUPID WAY, BUT SEEMS TO BE NO OTHER CHOICE)
        # Get all actors in level
        level_actors = unreal.EditorLevelLibrary.get_all_level_actors()
        actors = []

        # Compare actor guids
        for level_actor in level_actors:
            for guid in guids:
                if unreal.GuidLibrary.equal_equal_guid_guid(level_actor.get_editor_property('actor_guid'), guid):
                    actors.append(level_actor)
                    break

        # Select actors
        unreal.EditorLevelLibrary.set_selected_level_actors(actors)

        return True    

    @unreal.ufunction(params=[str, unreal.Array(str), bool], ret=str, static=True)
    def search_for_asset(root_folder="/Game/", filters=[], search_complete_path=True):
        """
        Returns a list of all the assets that include the file filters

        :return: *list*
        """
        filtered_assets = []

        assets =  unreal.EditorAssetLibrary.list_assets(root_folder)

        assets = [path for path in assets if path.startswith(root_folder)]

        for asset in assets:
            for file_filter in filters:
                if not search_complete_path:
                    if file_filter.lower() in os.path.basename(asset).lower():
                        filtered_assets.append(asset)
                else:
                    if file_filter.lower() in asset.lower():
                        filtered_assets.append(asset)

        return str(filtered_assets)    


"""
General helper functions    
"""    
  
def match_existing_folder_case(input_path="/Game/developers"):
    """
    Match the case sensitivity of existing folders on disk, so we don't submit perforce paths with mismatched casing
    """
    input_path = input_path.replace("\\", "/")

    project_content_path = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())
    project_disk_path = pathlib.Path(project_content_path).resolve().as_posix() + "/"

    disk_path = input_path.replace("/Game/", project_disk_path)

    # this is the magic line that makes it match the local disk
    case_sensitive_path = pathlib.Path(disk_path).resolve().as_posix()

    matched_path = case_sensitive_path.replace(project_disk_path, "/Game/")

    # make sure trailing slashes is preserved
    if input_path.endswith("/"):
        matched_path = f"{matched_path}/"

    if matched_path != input_path:
        print(f"Incorrectly cased path '{input_path}' was converted to '{matched_path}'")

    return matched_path

def show_dialog_confirm(title, message):
    """
    Show a dialog with YES/NO options.

    :return: *bool* true/false depending on which button is clicked
    """
    message_type = unreal.AppMsgType.YES_NO
    return_value = unreal.EditorDialog.show_message(title, message, message_type)

    return return_value

```

# Unreal Client

A SkyHook client for Unreal works exactly the same as for a normal SkyHook server.

```python
from skyhook import client

client = client.UnrealClient()

result = client.execute("search_for_asset", {"root_folder": "/Game", "filters": ["SK_Char"]})
print(result.get("ReturnValue", None))

# >> [/Game/ArcRaiders/Characters/SK_Character01.SK_Character01, /Game/ArcRaiders/Characters/SK_Character02.SK_Character02, /Game/ArcRaiders/Props/SK_CharredHusk.SK_CharredHusk]
```

---
**NOTE**

Due to how Unreal processes Python commands, you can't skip an argument or keyword argument when calling a function. In the example above, doing something like this will cause an error in Unreal

```python
client.execute("search_for_asset", {"filters": ["SK_Char"]}) # not passing the first keyword argument (`root_folder`)
# -> errors out in Unreal
```

---


## Contributing

[![Contributor Covenant](https://img.shields.io/badge/contributor%20covenant-v1.4-ff69b4.svg)](../main/CODE_OF_CONDUCT.md)

We welcome community contributions to this project.

Please read our [Contributor Guide](CONTRIBUTING.md) for more information on how to get started.

## License

Licensed under either of

* Apache License, Version 2.0, ([LICENSE-APACHE](LICENSE-APACHE) or http://www.apache.org/licenses/LICENSE-2.0)
* MIT license ([LICENSE-MIT](LICENSE-MIT) or http://opensource.org/licenses/MIT)

at your option.

### Contribution

Unless you explicitly state otherwise, any contribution intentionally submitted for inclusion in the work by you, as defined in the Apache-2.0 license, shall be dual licensed as above, without any additional terms or conditions.
