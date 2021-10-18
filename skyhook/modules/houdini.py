try:
    import hou
except:
    pass

def say_hi_from_houdini():
    """
    This says Hi in Houdini

    :return: *string*
    """
    print("Hi from Houdini!")
    return("I said hi")

def create_node(path, type, name="NisseNode"):
    obj = hou.node(path)
    obj.createNode(type, name)


def run_python_script(script_path):
    import runpy
    runpy.run_path(script_path, init_globals=globals(), run_name="__main__")
