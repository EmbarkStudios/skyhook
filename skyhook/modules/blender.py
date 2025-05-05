"""
Just some examples to help you get on your way with adding in functionality. 

"""


try:
    import bpy
except:
    pass

def make_cube():
    try:
        with bpy.context.temp_override(**__get_window_ctx()):
            bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
    except Exception as e:
        return f"Cube failed: {str(e)}"


def make_cube_at_location(location=(0, 0, 0)):
    with bpy.context.temp_override(**__get_window_ctx()):
        bpy.ops.mesh.primitive_cube_add(location=location)


def export_to_usd(filepath="C:/tmp/test.usd", selected_only= True):
    """
    Example to export to USD.
    """
    try:
        bpy.ops.wm.usd_export(
            filepath=filepath,
            check_existing=False,
            selected_objects_only=selected_only,
            visible_objects_only=True,
            export_materials=False,
            generate_preview_surface=False,
            export_textures=False,
            use_instancing=True,
            relative_paths=True,
            export_normals=True,
        )
        return "Export completed successfully"
    except Exception as e:
        return f"Export failed: {str(e)}"


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
    Gets a more complete Window Context for blender operations.
    """
    window = bpy.context.window_manager.windows[0]
    screen = window.screen
    
    # Find a 3D view area
    areas_3d = [area for area in screen.areas if area.type == 'VIEW_3D']
    if areas_3d:
        area = areas_3d[0]
        region = [region for region in area.regions if region.type == 'WINDOW'][0]
    else:
        # Fallback to any area
        area = screen.areas[0]
        region = area.regions[0]
    
    ctx = {
        'window': window,
        'screen': screen,
        'area': area,
        'region': region,
        'scene': bpy.context.scene,
        'view_layer': bpy.context.view_layer,
    }
    return ctx