class Constants:
    """
    Some very general constants that are used throughout SkyHook
    """
    function_name   = "FunctionName"
    parameters      = "Parameters"
    module          = "_Module"
    undefined       = "undefined"

    is_skyhook_module = "is_skyhook_module"


class Results:
    time            = "Time"
    success         = "Success"
    return_value    = "ReturnValue"
    command         = "Command"


class Ports:
    """
    Ports that the host programs use and for the clients to connect to
    """
    undefined         = 65500
    maya              = 65501
    houdini           = 65502
    blender           = 65504
    substance_painter = 65505
    unreal            = 30010


class HostPrograms:
    """
    List of host programs
    """
    blender           = "blender"
    unreal            = "unreal"
    maya              = "maya"
    houdini           = "houdini"
    substance_painter = "substance_painter"


class ServerCommands:
    """
    These are commands that are not run from any modules, but in the server class. In case of Unreal, since we don't
    control the server, these commands will have to be overridden in the client.
    """
    SKY_SHUTDOWN       = "SKY_SHUTDOWN"
    SKY_LS             = "SKY_LS"
    SKY_RELOAD_MODULES = "SKY_RELOAD_MODULES"
    SKY_HOTLOAD        = "SKY_HOTLOAD"
    SKY_UNLOAD         = "SKY_UNLOAD"
    SKY_FUNCTION_HELP  = "SKY_FUNCTION_HELP"


class Errors:
    """
    Errors when things go wrong
    """
    CALLING_FUNCTION = "An error occurred when calling the function"
    IN_FUNCTION      = "An error occurred when executing the function"
    SERVER_COMMAND   = "An error occurred processing this server command"
    SERVER_RELOAD    = "An error occurred with reloading a module on the server"
    TIMEOUT          = "The command timed out"


class UnrealTypes:
    """
    Unreal object types as strings
    """
    STATICMESH = "StaticMesh"
    SKELETALMESH = "SkeletalMesh"
    TEXTURE2D = "Texture2D"
    MATERIAL = "Material"
    MATERIALINSTANCE = "MaterialInstance"
