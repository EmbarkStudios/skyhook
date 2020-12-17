try:
    import bpy
except:
    pass

def make_cube():
    """
    Make a cube
    :return:
    """
    bpy.ops.mesh.primitive_cube_add(__get_window_ctx(), location=(0, 0, 0))
    return "I made a cube!"

def make_cube_at_location(location=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(__get_window_ctx(), location=location)

def get_all_objects_in_scene():
    """
    Gets all the objects in the scene

    :return: *list* with object names
    """
    return [obj.name for obj in bpy.data.objects]

def say_hello():
    """
    Says hello!

    :return: *string*
    """
    print("Hello from Blender")
    return "I said hello in Blender"

def __get_window_ctx():
    """
    Gets the Window Context for blender. Any functionality that adds something to the viewport needs this context. Use
    it as the first argument when calling a function that

    :return:
    """
    window = bpy.context.window_manager.windows[0]
    ctx = {'window': window, 'screen': window.screen}
    return ctx