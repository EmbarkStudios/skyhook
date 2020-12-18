import sys

import wsgiref.simple_server
import threading
from datetime import datetime
import importlib
import inspect
import types
from functools import partial
import json
import traceback


try:
    from PySide2.QtCore import *
except:
    from PySide.QtCore import *
finally:
    pass

try:
    # Python 3
    import urllib.parse as urlparse
except:
    # Python 2
    import urlparse

try:
    # Python 3
    from importlib import reload
except:
    pass

try:
    # Python 3
    import http.server
    http.server.BaseHTTPRequestHandler.address_string = lambda x: x.client_address[0]
except:
    # Python 2
    __import__('BaseHTTPServer').BaseHTTPRequestHandler.address_string = lambda x: x.client_address[0]

try:
    import websockets
    import asyncio
except:
    print("Can't import websockets/asyncio")


from .constants import Constants, ServerCommands, Errors, Ports
from .modules import core


class MainThreadExecutor(QObject):
    """
    Some programs, like Blender, don't like it when things get executed outside the main thread. Since the SkyHook
    server needs to run in its own thread in order to not block the UI, Blender will crash if any bpy.ops commands
    are run in the server thread. This class can be spawned in the main UI thread. The server will communicate to it
    by emitting a signal that this class will catch. That way it can run bpy.ops code in the main thread instead of the
    server thread.
    """
    def __init__(self, server):
        super(MainThreadExecutor, self).__init__()
        self.server = server
        print("Executor started")

    def execute(self, function_name, parameters_dict):
        """
        Executes a function. The response from the SkyHook server will not be returned here, but set in the server's
        executor_reply property. When using a MainThreadExecutor, the server will block until its executor_reply
        property is set to anything but None.

        :param function_name: *string* name of the function, it will be searched for in the server
        :param parameters_dict: *dict* with parameters
        :return: None
        """
        parameters_dict.pop(Constants.module, None)
        function = self.server.get_function_by_name(function_name)
        try:
            return_value = function(**parameters_dict)
            success = True
        except Exception as err:
            str(traceback.format_exc())
            return_value = str(traceback.format_exc())
            success = False

        result_json = make_result_json(success, return_value, function_name)

        # self.send_result_signal.emit(result_json) # this currently doesn't work, so just setting it on server directly
        self.server.executor_reply = result_json


class Server(QObject):
    """
    Main SkyHook server class
    """
    is_terminated = Signal(str)
    exec_command_signal = Signal(str, dict)
    def __init__(self, host_program=None, load_modules=[], use_main_thread_executor=False, echo_response=True):
        super(Server, self).__init__()
        self.port = self.__get_host_program_port(host_program)
        self.__keep_running = True
        self.__host_program = host_program

        self.__use_main_thread_executor = use_main_thread_executor
        self.executor_reply = None

        self.__echo_response = echo_response

        self.__loaded_modules = []
        self.__loaded_modules.append(core)
        for module_name in load_modules:
            self.hotload_module(module_name)

    def reload_modules(self):
        """
        Reloads all the currently loaded modules. This can also be called remotely by sending
        ServerCommands.SKY_RELOAD_MODULES as the FunctionName. Will use importlib.reload if the server is running
        in Python 3

        :return: None
        """

        reload_module_names = []

        for module in self.__loaded_modules:
            try:
                reload(module)
                reload_module_names.append(module.__name__)
            except:
                importlib.reload(module)
        return reload_module_names

    def hotload_module(self, module_name, is_skyhook_module=True):
        """
        Tries to load a module with module_name from skyhook.modules to be added to the server while it's running.

        :param module_name: *string* name of the module you want to load
        :return: None
        """
        if isinstance(module_name, types.ModuleType):
            if is_skyhook_module:
                module_name = module_name.__name__.split(".")[-1]
            else:
                module_name = module_name.__name__
            print(module_name)


        try:
            if is_skyhook_module:
                mod = importlib.import_module(".modules.%s" % module_name, package="skyhook")
            else:
                mod = importlib.import_module(module_name)

            if not mod in self.__loaded_modules:
                self.__loaded_modules.append(mod)
                print("Added %s" % mod)
                print("Loaded modules:")
                print(self.__loaded_modules)
        except:
            print("Failed to hotload: %s" % module_name)

    def unload_modules(self, module_name, is_skyhook_module=True):
        """
        Removes a module from the server

        :param module_name: *string* name of the module you want to remove
        :param is_skyhook_module: *bool* set this to true if the module you want to remove is a skyhook module
        :return: None
        """
        if is_skyhook_module:
            full_name = "skyhook.modules." + module_name
        else:
            full_name = module_name
        for module in self.__loaded_modules:
            if module.__name__ == full_name:
                self.__loaded_modules.remove(module)

    def start_listening(self):
        """
        Starts the listening for incoming requests.

        :return: None
        """
        print("Starting server on port: %s" % self.port)
        try:
            simple_server = wsgiref.simple_server.make_server("127.0.0.1", self.port, self.__process_request)
            print(simple_server.server_address)
            while self.__keep_running:
                simple_server.handle_request()
            print("Stopped listening\n\n")
        except:
            print(traceback.format_exc())
            print("Can't start the server")

    # def start_websocket_listening(self):
    #     print("Starting websocket server on port: %s" % self.port)
    #     try:
    #         websocket_server = websockets.serve(self.__process_websocket_request, "127.0.0.1", self.port)
    #         while self.__keep_running:
    #             asyncio.get_event_loop().run_until_complete(websocket_server)
    #             asyncio.get_event_loop().run_forever()
    #     except:
    #         print("Failed to create websocket server")
    #
    # async def __process_websocket_request(self, websocket, path):
    #     request = await websocket.recv()
    #     print("I received this request: ", request)
    #     print("I'm going to send back the word 'sushi' to the client" )
    #     await websocket.send("sushi")

    def stop_listening(self):
        """
        Stops listening for incoming requests. Also emits the is_terminated signal with "TERMINATED"

        :return: None
        """
        self.__keep_running = False
        self.is_terminated.emit("TERMINATED")

    def get_function_by_name(self, function_name, module_name=None):
        """
        Tries to find a function by name.

        :param function_name: *string* name of the function you're looking for
        :param module_name: *string* name of the module to search in. If None, all modules are searched
        :return: the actual function that matches your name, or None
        """
        if module_name is not None:
            module = sys.modules.get(".modules.%s" % module_name)
            if module is not None:
                modules = [module]
            else:
                module = sys.modules.get(module_name)
                modules = [module]
        else:
            modules = self.__loaded_modules

        for module in modules:
            for name, value in module.__dict__.items():
                if callable(value):
                    if function_name == name:
                        return value

    def catch_executor_reply(self, reply_dict):
        """
        This is supposed to catch a signal coming from MainThreadExecutor, but it's not working as intended right now.
        Will have to look into it a bit more.

        :param reply_dict:
        :return:
        """
        print("Caught the reply from the executor!")
        print(reply_dict)
        self.executor_reply = reply_dict

    def __process_request(self, environ, start_response):
        """
        This function is called on every incoming request. It calls the __filter_command function to see what
        should happen with the request.

        You shouldn't call this function directly.

        :param environ:
        :param start_response:
        :return:
        """
        status = "200 OK"
        headers = [("Content-type", "text/plain")]
        start_response(status, headers)
        request_body_size = int(environ.get('CONTENT_LENGTH', 0))
        request_body = environ['wsgi.input'].read(request_body_size)
        query = json.loads(request_body)

        function = query.get(Constants.function_name)
        parameters = query.get(Constants.parameters)

        command_response = self.__filter_command(function, parameters)

        if self.__echo_response:
            print(command_response)

        return command_response

    def __filter_command(self, function_name, parameters_dict):
        """
        This function decides whether or the function call should come from one of the loaded modules or from the server.
        Every server function should start with SKY_

        You shouldn't call this function directly.

        :param function_name:
        :param parameters_dict:
        :return:
        """
        if function_name in dir(ServerCommands):
            result_json = self.__process_server_command(function_name, parameters_dict)
        else:
            result_json = self.__process_module_command(function_name, parameters_dict)

        self.executor_reply = None
        return [json.dumps(result_json).encode()]

    def __process_server_command(self, function_name, parameters_dict={}):
        """
        Processes a command if the function in it was a server function.

        You shouldn't call this function directly

        :param function_name:
        :return:
        """
        result_json = make_result_json(False, Errors.SERVER_COMMAND, None)

        if function_name == ServerCommands.SKY_SHUTDOWN:
            self.stop_listening()
            result_json = make_result_json(True, "Server offline", ServerCommands.SKY_SHUTDOWN)

        elif function_name == ServerCommands.SKY_LS:
            functions = []
            for module in self.__loaded_modules:
                functions.extend([func for func in dir(module) if not "__" in func or isinstance(func, types.FunctionType)])
            result_json = make_result_json(True, functions, ServerCommands.SKY_LS)

        elif function_name == ServerCommands.SKY_RELOAD_MODULES:
            reloaded_modules = self.reload_modules()
            result_json = make_result_json(True, reloaded_modules, ServerCommands.SKY_RELOAD_MODULES)

        elif function_name == ServerCommands.SKY_HOTLOAD:
            modules = parameters_dict.get(Constants.module)
            is_skyhook_module = parameters_dict.get("is_skyhook_module", True)

            hotloaded_modules = []
            for module_name in modules:
                try:
                    self.hotload_module(module_name, is_skyhook_module=is_skyhook_module)
                    hotloaded_modules.append(module_name)
                except:
                    pass

            result_json = make_result_json(True, hotloaded_modules, ServerCommands.SKY_HOTLOAD)

        elif function_name == ServerCommands.SKY_UNLOAD:
            modules = parameters_dict.get(Constants.module)
            for module in modules:
                self.unload_modules(module)

            result_json = make_result_json(True, [m.__name__ for m in self.__loaded_modules], ServerCommands.SKY_UNLOAD)

        elif function_name == ServerCommands.SKY_FUNCTION_HELP:
            function_name = parameters_dict.get("function_name")
            function = self.get_function_by_name(function_name)
            arg_spec = inspect.getargspec(function)

            arg_spec_dict = {}
            arg_spec_dict["function_name"] = function_name
            arg_spec_dict["arguments"] = arg_spec.args
            if arg_spec.varargs is not None:
                arg_spec_dict["packed_args"] = "*%s" % arg_spec.varargs
            if arg_spec.keywords is not None:
                arg_spec_dict["packed_kwargs"] = "**%s" % arg_spec.keywords

            result_json = make_result_json(True, arg_spec_dict, ServerCommands.SKY_FUNCTION_HELP)

        return result_json

    def __process_module_command(self, function_name, parameters_dict):
        """
        Processes a command if the function in it was a module function.

        You shouldn't call this function directly

        :param function_name:
        :param parameters_dict:
        :return:
        """
        if self.__use_main_thread_executor:
            print("Emitting exec_command_signal")
            self.exec_command_signal.emit(function_name, parameters_dict)

            while self.executor_reply is None:
                pass
            return self.executor_reply

        module = parameters_dict.get(Constants.module)
        parameters_dict.pop(Constants.module, None) # remove module from the parameters, otherwise it gets passed to the function
        function = self.get_function_by_name(function_name, module)

        try:
            return_value = function(**parameters_dict)
            success = True
        except Exception as err:
            str(traceback.format_exc())
            return_value = str(traceback.format_exc())
            success = False

        result_json = make_result_json(success, return_value, function_name)
        return result_json

    def __get_host_program_port(self, host_program):
        """
        Looks through the Constants.Ports class to try and find the port for the host program. If it can't, it will
        default to Constants.Ports.undefined

        You shouldn't call this function directly

        :param host_program: *string* name of the host program
        :return:
        """
        try:
            return getattr(Ports, host_program)
        except AttributeError:
            return getattr(Ports, Constants.undefined)



def make_result_json(success, return_value, command):
    """
    Constructs the a json for the server to send back

    :param success:
    :param return_value:
    :return:
    """
    result_json = {
        "Time": datetime.now().strftime("%H:%M:%S"),
        "Success": success,
        "ReturnValue": return_value,
        "Command": command
    }

    return result_json


def start_server_in_thread(host_program="", load_modules=[]):
    """
    Starts a server in a separate QThread. Use this when working in Houdini or Maya.

    :param host_program: *string* name of the host program
    :param load_modules: *list* modules to load
    :return: *QThread* and *Server*
    """
    skyhook_server = Server(host_program=host_program, load_modules=load_modules)
    thread_object = QThread()
    skyhook_server.is_terminated.connect(partial(__kill_thread, thread_object))
    skyhook_server.moveToThread(thread_object)

    thread_object.started.connect(skyhook_server.start_listening)
    thread_object.start()

    return [thread_object, skyhook_server]

def start_executor_server_in_thread(host_program="", load_modules=[]):
    """
    Starts a server in a thread, but moves all executing functionality to a MainThreadExecutor object. Use this
    for a host program where executing code in a thread other than the main thread is not safe. Eg: Blender

    :param host_program: *string* name of the host program
    :param load_modules: *list* modules to load
    :return: *QThread*, *MainThreadExecutor* and *Server*
    """
    skyhook_server = Server(host_program=host_program, load_modules=load_modules, use_main_thread_executor=True)
    executor = MainThreadExecutor(skyhook_server)
    skyhook_server.exec_command_signal.connect(executor.execute)

    thread_object = QThread()
    skyhook_server.moveToThread(thread_object)
    thread_object.started.connect(skyhook_server.start_listening)
    thread_object.start()

    return [thread_object, executor, skyhook_server]

def start_python_thread_server(host_program="", load_modules=[]):
    """
    Starts a server in a separate Python thread if for whatever reason a QThread won't work

    :param host_program: *string* name of the host program
    :param load_modules: *list* modules to load
    :return: *Server*
    """
    skyhook_server = Server(host_program=host_program, load_modules=load_modules, use_main_thread_executor=False)
    thread = threading.Thread(target=skyhook_server.start_listening)
    thread.setDaemon(True)
    thread.start()

    return skyhook_server

def start_blocking_server(host_program="", load_modules=[]):
    """
    Starts a server in the main thread. This will block your application. Use this when you don't care about your
    application being locked up.

    :param host_program: *string* name of the host program
    :param load_modules: *list* modules to load
    :return: *Server*
    """
    skyhook_server = Server(host_program=host_program, load_modules=load_modules)
    skyhook_server.start_listening()
    return skyhook_server

# def start_blocking_websocket_server(host_program=""):
#     """
#     Starts a websocket server in the main thread. This will block your application. Use this when you don't care about
#     your application being locked up.
#
#     :param host_program:
#     :return:
#     """
#     skyhook_websocket_server = Server(host_program=host_program)
#     skyhook_websocket_server.start_websocket_listening()
#     return skyhook_websocket_server

def __kill_thread(thread, _):
    """
    Kills a QThread

    :param thread: QThread object you want to kill
    :param _: this is garbage variable
    :return:
    """
    thread.exit()
    print("\nShyhook server thread was killed")
