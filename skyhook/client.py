import pprint

from .constants import HostPrograms, Results, Ports, ServerCommands
import requests

try:
    import websockets
    import asyncio
except:
    pass
    # print("failed to import websockets/asyncio")

class Client(object):
    """
    Base client from which all other Clients will inherit
    """
    def __init__(self, port=Ports.undefined, host_address="127.0.0.1", timeout=1):
        super(Client, self).__init__()

        self.host_address = host_address
        self.port = port
        self.timeout = timeout

        self.__echo_execution = True
        self.__echo_payload = True
        self._is_executing = False

    def set_echo_execution(self, value):
        """
        If set to true, the client will print out the response coming from the server

        :param value: *bool*
        :return: None
        """
        self.__echo_execution = value

    def echo_execution(self):
        """
        Return True or False whether or not responses from the server are printed in the client

        :return: *bool*
        """
        return self.__echo_execution

    def set_echo_payload(self, value):
        """
        If set to true, the client will print the JSON payload it's sending to the server

        :param value: *bool*
        :return:
        """
        self.__echo_payload = value

    def echo_payload(self):
        """
        Return True or False whether or not the JSON payloads sent to the server are printed in the client

        :return:
        """
        return self.__echo_payload

    def is_executing(self):
        """
        Retrun True or False if the client is still executing a command

        :return: *bool*
        """
        return self._is_executing

    def is_host_online(self):
        """
        Convenience function to call on the client. "is_online" comes from the core module

        :return: *bool*
        """
        response = self.execute("is_online", {})
        return response.get("Success")


    def execute(self, command, parameters={}, timeout=0):
        """
        Executes a given command for this client. The server will look for this command in the modules it has loaded

        :param command: *string* or *function* The command name or the actual function object that you can import from the modules module
        :param parameters: *dict* of the parameters (arguments) for the the command. These have to match the argument names on the function in the module exactly
        :param timeout: *float* time in seconds after which the request will timeout. If not set here, self.time_out will be used (1.5 by default)
        :return: *dict* of the response coming from the server

        From a SkyHook server it looks like:
        {
             'ReturnValue': ['Camera', 'Cube', 'Cube.001', 'Light'],
             'Success': True,
             'Time': '09:43:18'
        }


        From Unreal it looks like this:
        {
            'ReturnValue': ['/Game/Developers/cooldeveloper/Maps/ScatterDemoLevel/ScatterDemoLevelMaster.ScatterDemoLevelMaster',
                            '/Game/Apple/Core/UI/Widgets/WBP_CriticalHealthLevelVignette.WBP_CriticalHealthLevelVignette',
                            '/Game/Apple/Lighting/LUTs/RGBTable16x1_Level_01.RGBTable16x1_Level_01']
        }
        """
        self._is_executing = True
        if timeout <= 0:
            timeout = self.timeout

        if callable(command):
            command = command.__name__

        url = "http://%s:%s" % (self.host_address, self.port)
        payload = self.__create_payload(command, parameters)
        response = requests.post(url, json=payload, timeout=timeout).json()

        if self.echo_payload():
            pprint.pprint(payload)

        if self.echo_execution():
            pprint.pprint(response)

        self._is_executing = False

        return response

    def __create_payload(self, command, parameters):
        """
        Constructs the dictionary for the JSON payload that will be sent to the server

        :param command: *string* name of the command
        :param parameters: *dictionary*
        :return: *dictionary*
        """
        payload = {
            "FunctionName": command,
            "Parameters": parameters
        }

        return payload

class SubstancePainterClient(Client):
    """
    Custom client for Substance Painter
    """
    def __init__(self, port=Ports.substance_painter, host_address="127.0.0.1"):
        super().__init__(port=port, host_address=host_address)
        self.host_program = HostPrograms.substance_painter


class BlenderClient(Client):
    """
    Custom client for Blender
    """
    def __init__(self, port=Ports.blender, host_address="127.0.0.1"):
        super().__init__(port=port, host_address=host_address)
        self.host_program = HostPrograms.blender


class MayaClient(Client):
    """
    Custom client for Maya
    """
    def __init__(self, port=Ports.maya, host_address="127.0.0.1"):
        super().__init__(port=port, host_address=host_address)
        self.host_program = HostPrograms.maya


class HoudiniClient(Client):
    """
    Custom client for Houdini
    """
    def __init__(self, port=Ports.houdini, host_address="127.0.0.1"):
        super().__init__(port=port, host_address=host_address)
        self.host_program = HostPrograms.houdini


class UnrealClient(Client):
    """
    Custom client for Unreal. This overwrites most of the basic functionality because we can't run a Skyhook server
    in Unreal, but have to rely on Web Remote Control.

    There is a file called skyhook in /Game/Python/ that holds the SkyHook classes to be used with this client.
    This file has to be loaded by running "import skyhook" in Unreal's Python editor, or imported when the project
    is loaded.

    """

    def __init__(self, port=Ports.unreal, host_address="127.0.0.1"):
        super().__init__(port=port, host_address=host_address)
        self.host_program = HostPrograms.unreal
        self.__command_object_path = "/Engine/PythonTypes.Default__SkyHookCommands"
        self.__server_command_object_path = "/Engine/PythonTypes.Default__SkyHookServerCommands"
        self.__headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

    def execute(self, command, parameters={}, timeout=0, function=True, property=False):
        """
        Will execute the command so Web Remote Control understands it.

        :param command: *string* command name
        :param parameters: *dict* of the parameters (arguments) for the the command. These have to match the argument names on the function in the module exactly
        :param timeout: *float* time in seconds after which the request will timeout. If not set here, self.time_out will be used (1.5 by default)
        :param function: *bool* ignore, not used
        :param property: *bool* ignore, not used
        :return: *dict* of the response coming from Web Remote Control
        """
        self._is_executing = True
        if timeout <= 0:
            timeout = self.timeout

        url = "http://%s:%s/remote/object/call" % (self.host_address, self.port)

        if command in dir(ServerCommands):
            payload = self.__create_payload(command, parameters, self.__server_command_object_path)
            used_object_path = self.__server_command_object_path
        else:
            payload = self.__create_payload(command, parameters, self.__command_object_path)
            used_object_path = self.__command_object_path

        try:
            response = requests.put(url, json=payload, headers=self.__headers, timeout=timeout).json()
        except requests.exceptions.ConnectionError:
            response = {"ReturnValue": False}

        try:
            # UE 4.26: Returning an unreal.Array() that's not empty crashes the editor
            # (https://udn.unrealengine.com/s/question/0D52L00005KOA24SAH/426-crashes-when-trying-to-return-an-unrealarray-over-web-remote-control-from-python)
            # The (ugly) workaround for this is to return the list as a string eg "['/Game/Content/file', '/Game/Content/file2']"
            # Then we try to eval the string here, if it succeeds, we'll have the list.

            # However!
            # This actually serves another purpose. It's much easier to return a dictionary from Unreal as a string compared
            # to an unreal.Map. When returning the stringified dict, you don't need to explicitly tell Unreal what type
            # the keys and values are. It also gets around errors like the following:
            #
            # -------------------------------------------------------------------------------------------------------
            # `TypeError: Map: 'value' (Array (IntProperty)) cannot be a container element type (directly nested
            # containers are not supported - consider using an intermediary struct instead)`
            # -------------------------------------------------------------------------------------------------------
            #
            # You'd get this error in Uneal when you try to declare the return type of a function as `unreal.Map(str, unreal.Array(int)`
            # When you'd want the value of the keys to be a list of ints, for example.

            # On top of that, stringifying a dict also just lets you return a bunch of values that are not all the same type.
            # As long as it can gets serialized into a JSON object, it will come out this end as a proper dictionary.
            evalled_return_value = eval(response.get(Results.return_value))
            response = {Results.return_value: evalled_return_value}
        except:
            pass

        if self.echo_payload():
            pprint.pprint(payload)

        if self.echo_execution():
            pprint.pprint(response)

        self._is_executing = False

        return response

    def set_command_object_path(self, path="/Engine/PythonTypes.Default__PythonClassName"):
        """
        Set the object path for commands

        :param path: *string* path. For Python functions, this has to be something like /Engine/PythonTypes.Default__<PythonClassName>
        You need to add the leading 'Default__', this is what Unreal Engine expects
        :return: None
        """
        self.__command_object_path = path

    def command_object_path(self):
        """
        Gets the command object path

        :return: *string* Object path
        """
        return self.__command_object_path

    def __create_payload(self, command, parameters, object_path, echo_payload=True):
        payload = {
            "ObjectPath": object_path,
            "FunctionName": command,
            "Parameters": parameters,
            "GenerateTransaction": True
        }

        return payload

# class WebsocketClient(Client):
#     def __init__(self):
#         super(WebsocketClient, self).__init__()
#         self.uri = "ws://%s:%s" % (self.host_address, self.port)
#         print(self.uri)
#
#     def execute(self, command, parameters={}):
#         payload = self.__create_payload(command, parameters)
#         print(payload)
#
#         async def send():
#             async with websockets.connect(self.uri) as websocket:
#                 await websocket.send(payload)
#                 response = await websocket.recv()
#                 return response
#
#         response = asyncio.get_event_loop().run_until_complete(send())
#         return response
#
#     def __create_payload(self, command, parameters):
#         """
#         Constructs the dictionary for the JSON payload that will be sent to the server
#
#         :param command: *string* name of the command
#         :param parameters: *dictionary*
#         :return: *dictionary*
#         """
#         payload = {
#             "FunctionName": command,
#             "Parameters": parameters
#         }
#
#         return payload
