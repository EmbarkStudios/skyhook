import traceback
try:
    import pymel.core as pm
    import maya.cmds as cmds
    import maya.utils as utils
except:
    print(str(traceback.format_exc()))
    pass


def make_cube():
    """
    Example function that will make a cube named Nisse

    :return:
    """
    pm.polyCube(name="Nisse")
    return None

def make_sphere(name="Nisse", create_uvs=1, radius=3):
    """
    Example function that will make a sphere name Nisse

    :return:
    """
    pm.polySphere(name=name, createUVs=create_uvs, radius=radius)
    return "I made a sphere"

def raw_maya(command, args=[], kwargs={}):
    """
    Handle a "raw" maya.cmds or pymel command. Expects args to be a list and kwargs to be a dictionary.

    Eg::
    import skyhook.client
    maya_client = skyhook.client.MayaClient()
    maya_client.execute("raw_maya", {"command": "pm.polySphere", "kwargs": {"radius": 20}})


    :param command: *string* of complete command. eg: pm.ls or cmds.polyCube
    :param args: *list* of unnamed arguments
    :param kwargs: *dict* with keywords that are needed for your command
    :return: *string* of whatever the command returned in Maya
    """
    kwargs = dict((str(k), v) for k, v in kwargs.items())
    # look the command up by name instead of eval()-ing it, so the command string can't be arbitrary Python
    module_name, _, func_name = command.partition(".")
    modules = {"pm": pm, "cmds": cmds}
    if module_name not in modules or not func_name or func_name.startswith("_"):
        raise ValueError(f"command must look like pm.<command> or cmds.<command>, got: {command}")
    func = getattr(modules[module_name], func_name)
    print(kwargs)


    result = func(*args, **kwargs)
    return str(result)


def warning(message):
    pm.warning(message)


def new_scene():
    pm.newFile(force=True)
