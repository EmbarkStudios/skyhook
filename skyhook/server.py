import sys

from PySide2.QtCore import *
from datetime import datetime
from functools import partial
from importlib import reload
from http.server import BaseHTTPRequestHandler, HTTPServer
import socket
import time
import importlib
import inspect
import types
import json
import traceback
import threading
import urllib.parse

from .logger import Logger
logger = Logger()

from .constants import Constants, Results, ServerCommands, Errors, Ports
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
        logger.info("Executor started")

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
            logger.success("MainThreadExecutor executed %s" % function)
        except Exception as err:
            trace = str(traceback.format_exc())
            return_value = trace
            success = False
            logger.error("MainThreadExecutor couldn't execute %s " % function)
            logger.error(str(err))
            logger.error(trace)

        result_json = make_result_json(success, return_value, function_name)

        # self.send_result_signal.emit(result_json) # this currently doesn't work, so just setting it on server directly
        self.server.executor_reply = result_json


class Server(QObject):
    """
    Main SkyHook server class

    There are 3 signals that you can hook into from the outside:
    is_terminated: emits when stop_listening() is called
    exec_command_signal: emits the command name and the parameter dictionary when a non-server command is
                         executed through the MainThreadExecutor
    command_signal: will always emit the command name and parameter dictionary,
                    whether the command was a non-server or server command
    """
    is_terminated = Signal(str)
    exec_command_signal = Signal(str, dict)
    command_signal = Signal(str, dict)

    def __init__(self, host_program=None, port=None, load_modules=[], use_main_thread_executor=False, echo_response=True):
        super().__init__()
        self.__host_program = host_program
        if port:
            self.port = port
        else:
            self.port = self.__get_host_program_port(host_program)
        self.__keep_running = True

        self.__use_main_thread_executor = use_main_thread_executor
        self.executor_reply = None
        self.__http_server = None

        self.__echo_response = echo_response

        self.__loaded_modules = []
        self.__loaded_modules.append(core)
        for module_name in load_modules:
            self.hotload_module(module_name)

    def start_listening(self):
        """
        Creates a RequestHandler and starts the listening for incoming requests. Will continue to listen for requests
        until self.__keep_running is set to False

        :return: None
        """
        def handler(*args):
            SkyHookHTTPRequestHandler(skyhook_server=self, *args)

        self.__http_server = HTTPServer(("127.0.0.1", self.port), handler)
        logger.info("Started SkyHook on port: %s" % self.port)
        while self.__keep_running:
            self.__http_server.handle_request()
        logger.info("Shutting down server")
        self.__http_server.server_close()
        logger.info("Server shut down")


    def stop_listening(self):
        """
        Stops listening for incoming requests. Also emits the is_terminated signal with "TERMINATED"

        :return: None
        """
        self.__keep_running = False
        self.__http_server.server_close()
        self.is_terminated.emit("TERMINATED")

    def reload_modules(self):
        """
        Reloads all the currently loaded modules. This can also be called remotely by sending
        ServerCommands.SKY_RELOAD_MODULES as the FunctionName.

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
        :param is_skyhook_module: *bool* name of the module you want to load
        :return: None
        """
        if isinstance(module_name, types.ModuleType):
            if is_skyhook_module:
                module_name = module_name.__name__.split(".")[-1]
            else:
                module_name = module_name.__name__

        try:
            if is_skyhook_module:
                mod = importlib.import_module(".modules.%s" % module_name, package="skyhook")
            else:
                mod = importlib.import_module(module_name)

            if not mod in self.__loaded_modules:
                self.__loaded_modules.append(mod)
                logger.info("Added %s" % mod)
                logger.info(self.__loaded_modules)
        except:
            logger.error("Failed to hotload: %s" % module_name)

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
        logger.info("Caught the reply from the executor!")
        logger.info(reply_dict)
        self.executor_reply = reply_dict

    def filter_and_execute_function(self, function_name, parameters_dict):
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
        return json.dumps(result_json).encode()

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
            is_skyhook_module = parameters_dict.get(Constants.is_skyhook_module, True)

            hotloaded_modules = []
            for module_name in modules:
                try:
                    self.hotload_module(module_name, is_skyhook_module=is_skyhook_module)
                    hotloaded_modules.append(module_name)
                except:
                    logger.info(Errors.SERVER_COMMAND, module_name)
                    logger.info(traceback.format_exc())

            result_json = make_result_json(True, hotloaded_modules, ServerCommands.SKY_HOTLOAD)

        elif function_name == ServerCommands.SKY_UNLOAD:
            modules = parameters_dict.get(Constants.module)
            for module in modules:
                self.unload_modules(module)

            result_json = make_result_json(True, [m.__name__ for m in self.__loaded_modules], ServerCommands.SKY_UNLOAD)

        elif function_name == ServerCommands.SKY_FUNCTION_HELP:
            function_name = parameters_dict.get("function_name")
            function = self.get_function_by_name(function_name)
            arg_spec = inspect.getfullargspec(function)

            arg_spec_dict = {}
            arg_spec_dict["function_name"] = function_name
            arg_spec_dict["arguments"] = arg_spec.args
            if arg_spec.varargs is not None:
                arg_spec_dict["packed_args"] = "*%s" % arg_spec.varargs
            if arg_spec.keywords is not None:
                arg_spec_dict["packed_kwargs"] = "**%s" % arg_spec.keywords

            result_json = make_result_json(True, arg_spec_dict, ServerCommands.SKY_FUNCTION_HELP)

        self.command_signal.emit(function_name, {})
        logger.success("Executed %s" % function_name)

        return result_json

    def __process_module_command(self, function_name, parameters_dict, timeout=10.0):
        """
        Processes a command if the function in it was a module function.

        You shouldn't call this function directly

        :param function_name:
        :param parameters_dict:
        :return:
        """
        if self.__use_main_thread_executor:
            logger.debug("Emitting exec_command_signal")
            self.exec_command_signal.emit(function_name, parameters_dict)
            start_time = time.time()

            while self.executor_reply is None:
                # wait for the executor to reply, just keep checking the time to see if we've waited longer
                # than timeout permits
                current_time = time.time()
                if current_time - start_time > timeout:
                    self.executor_reply = make_result_json(success=False, return_value=Errors.TIMEOUT, command=function_name)
            return self.executor_reply

        module = parameters_dict.get(Constants.module)
        parameters_dict.pop(Constants.module, None) # remove module from the parameters, otherwise it gets passed to the function
        function = self.get_function_by_name(function_name, module)

        try:
            return_value = function(**parameters_dict)
            success = True
            self.command_signal.emit(function_name, parameters_dict)
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
        except Exception:
            return getattr(Ports, Ports.undefined)

class SkyHookHTTPRequestHandler(BaseHTTPRequestHandler):
    """
    The class that handles requests coming into the server. It holds a reference to the Server class, so
    it can call the Server functions after it has processed the request.

    """
    skyhook_server: Server # for PyCharm autocomplete

    def __init__(self, request, client_address, server, skyhook_server=None, reply_with_auto_close=True):
        self.skyhook_server = skyhook_server
        self.reply_with_auto_close = reply_with_auto_close
        super().__init__(request, client_address, server)

    def do_GET(self):
        """
        Handle a GET request, this would be just a browser requesting a particular url
        like: http://localhost:65500/%22echo_message%22&%7B%22message%22:%22Hooking%20into%20the%20Sky%22%7D
        """
        # browsers tend to send a GET for the favicon as well, which we don't care about
        if self.path == "/favicon.ico":
            return

        data = urllib.parse.unquote(self.path).lstrip("/")
        parts = data.split("&")

        try:
            function = eval(parts[0])
            parameters = json.loads(parts[1])
        except NameError as err:
            logger.warning(f"Got a GET request that I don't know what to do with")
            logger.warning(f"Request was: GET {data}")
            logger.warning(f"Error is   : {err}")
            return

        command_response = self.skyhook_server.filter_and_execute_function(function, parameters)
        self.send_response_data("GET")
        self.wfile.write(bytes(f"{command_response}".encode("utf-8")))
        if self.reply_with_auto_close:
            # reply back to the browser with a javascript that will close the window (tab) it just opened
            self.wfile.write(bytes("<script type='text/javascript'>window.open('','_self').close();</script>".encode("utf-8")))

    def do_POST(self):
        """
        Handle a post request, expects a JSON object to be sent in the POST data
        """
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        decoded_data = post_data.decode('utf-8')
        json_data = json.loads(decoded_data)

        function = json_data.get(Constants.function_name)
        parameters = json_data.get(Constants.parameters)

        command_response = self.skyhook_server.filter_and_execute_function(function, parameters)
        self.send_response_data("POST")
        self.wfile.write(command_response)

    def send_response_data(self, request_type):
        """
        Generates the response and appropriate headers to send back to the client

        :param request_type: *string* GET or POST
        """
        self.send_response(200)
        if request_type == "GET":
            self.send_header('Content-type', 'text/html')
        elif request_type == "POST":
            self.send_header('Content-type', 'application/json')
        else:
            pass
        self.end_headers()


def port_in_use(port_number, host="127.0.0.1"):
    """
    Checks if a specific ports is already in use by a different process. Useful if you want to check if you can start
    a SkyHook server on a default port that might already be in use.

    :param port_number: Port you want to check
    :param host: Hostname, default is 127.0.0.1
    :return:
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.125)
    result = sock.connect_ex((host, port_number))
    if result == 0:
        return True
    return False

def make_result_json(success, return_value, command):
    """
    Constructs the a json for the server to send back after a POST request

    :param success:
    :param return_value:
    :return:
    """
    result_json = {
        Results.time: datetime.now().strftime("%H:%M:%S"),
        Results.success: success,
        Results.return_value: return_value,
        Results.command: command
    }

    return result_json


def start_server_in_thread(host_program="", port=None, load_modules=[], echo_response=False):
    """
    Starts a server in a separate QThread. Use this when working in Houdini or Maya.

    :param host_program: *string* name of the host program
    :param port: *int* port override
    :param load_modules: *list* modules to load
    :param echo_response: *bool* print the response the server is sending back
    :return: *QThread* and *Server*
    """
    if host_program != "":
        port = getattr(Ports, host_program)

    if port_in_use(port):
        logger.error(f"Port {port} is already in use, can't start server")
        return [None, None]

    skyhook_server = Server(host_program=host_program, port=port, load_modules=load_modules, echo_response=echo_response)
    thread_object = QThread()
    skyhook_server.is_terminated.connect(partial(__kill_thread, thread_object))
    skyhook_server.moveToThread(thread_object)

    thread_object.started.connect(skyhook_server.start_listening)
    thread_object.start()

    return [thread_object, skyhook_server]


def start_executor_server_in_thread(host_program="", port=None, load_modules=[], echo_response=False):
    """
    Starts a server in a thread, but moves all executing functionality to a MainThreadExecutor object. Use this
    for a host program where executing code in a thread other than the main thread is not safe. Eg: Blender

    :param host_program: *string* name of the host program
    :param port: *int* port override
    :param load_modules: *list* modules to load
    :param echo_response: *bool* print the response the server is sending back
    :return: *QThread*, *MainThreadExecutor* and *Server*
    """
    if host_program != "":
        port = getattr(Ports, host_program)

    if port is None:
        port = getattr(Ports, Constants.undefined)

    if port_in_use(port):
        logger.error(f"Port {port} is already in use, can't start server")
        return [None, None, None]

    skyhook_server = Server(host_program=host_program, port=port, load_modules=load_modules,
                            use_main_thread_executor=True, echo_response=echo_response)
    executor = MainThreadExecutor(skyhook_server)
    skyhook_server.exec_command_signal.connect(executor.execute)

    thread_object = QThread()
    skyhook_server.is_terminated.connect(partial(__kill_thread, thread_object))
    skyhook_server.moveToThread(thread_object)
    thread_object.started.connect(skyhook_server.start_listening)
    thread_object.start()

    return [thread_object, executor, skyhook_server]


def start_python_thread_server(host_program="", port=None, load_modules=[], echo_response=False):
    """
    Starts a server in a separate Python thread if for whatever reason a QThread won't work

    :param host_program: *string* name of the host program
    :param port: *int* port override
    :param load_modules: *list* modules to load
    :param echo_response: *bool* print the response the server is sending back
    :return: *Server*
    """
    if host_program != "":
        port = getattr(Ports, host_program)

    if port is None:
        port = getattr(Ports, Constants.undefined)

    if port_in_use(port):
        logger.error(f"Port {port} is already in use, can't start server")
        return None

    skyhook_server = Server(host_program=host_program, port=port, load_modules=load_modules,
                            use_main_thread_executor=False, echo_response=echo_response)
    thread = threading.Thread(target=skyhook_server.start_listening)
    thread.setDaemon(True)
    thread.start()

    return skyhook_server


def start_blocking_server(host_program="", port=None, load_modules=[], echo_response=False):
    """
    Starts a server in the main thread. This will block your application. Use this when you don't care about your
    application being locked up.

    :param host_program: *string* name of the host program
    :param port: *int* port override
    :param load_modules: *list* modules to load
    :param echo_response: *bool* print the response the server is sending back
    :return: *Server*
    """
    if host_program != "":
        port = getattr(Ports, host_program)

    if port is None:
        port = getattr(Ports, Constants.undefined)

    if port_in_use(port):
        logger.error(f"Port {port} is already in use, can't start server")
        return None

    skyhook_server = Server(host_program=host_program, port=port, load_modules=load_modules, echo_response=echo_response)
    skyhook_server.start_listening()
    return skyhook_server


def __kill_thread(thread, _):
    """
    Kills a QThread

    :param thread: QThread object you want to kill
    :param _: this is garbage variable
    :return:
    """
    thread.exit()
    logger.info("\nShyhook server thread was killed")
