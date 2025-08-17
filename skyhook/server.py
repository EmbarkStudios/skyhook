import sys
import threading
import time
import socket
import importlib
import inspect
import types
import json
import traceback
import urllib.parse

from datetime import datetime
from importlib import reload
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List, Optional, TypeVar, Union, Callable, Type

from .constants import Constants, Results, ServerCommands, Errors, Ports, HostPrograms, ServerEvents
from .modules import core
from .logger import Logger

logger = Logger()

T = TypeVar('T')


class EventEmitter:
    """
    A simple event emitter similar to Qt's signal/slot mechanism.
    """

    def __init__(self) -> None:
        self._callbacks: Dict[str, List[Callable[..., Any]]] = {}

    def connect(self, event_name: str, callback: Callable[..., Any]) -> None:
        """
        Connect a callback to an event
        """
        if event_name not in self._callbacks:
            self._callbacks[event_name] = []
        self._callbacks[event_name].append(callback)

    def emit(self, event_name: str, *args: Any, **kwargs: Any) -> None:
        """
        Emit an event with arguments
        """
        if event_name in self._callbacks:
            for callback in self._callbacks[event_name]:
                callback(*args, **kwargs)


class GenericMainThreadExecutor:
    """
    You can spawn an object of this class in the main thread of a program, while the server runs in a different thread. Any code
    execution will happen in the main thread and the server can run on a separate, non-blocking thread. Useful when you're
    running a Skyhook server inside another program. 
    """

    def __init__(self, server: 'Server') -> None:
        self.server: 'Server' = server
        logger.info(f"Executor started: {type(self)}")

    def execute(self, function_name: str, parameters_dict: Dict[str, Any]) -> None:
        """
        Executes a function. The response from the SkyHook server will not be returned here, but set in the server's
        executor_reply property. When using a MainThreadExecutor, the server will block until its executor_reply
        property is set to anything but None.

        :param function_name: *string* name of the function, it will be searched for in the server
        :param parameters_dict: *dict* with parameters
        :return: None
        """
        parameters_dict.pop(Constants.module, None)
        function: Callable[..., Any] = self.server.get_function_by_name(function_name)
        try:
            return_value: Any = function(**parameters_dict)
            success: bool = True
            logger.success(f"MainThreadExecutor executed {function}")
        except Exception as err:
            trace: str = str(traceback.format_exc())
            return_value = trace
            success = False
            logger.error(f"MainThreadExecutor couldn't execute {function}")
            logger.error(str(err))
            logger.error(trace)

        result_json: Dict[str, Any] = make_result_json(success, return_value, function_name)
        self.server.executor_reply = result_json


class MayaExecutor(GenericMainThreadExecutor):
    """
    A specific MainThreadExecutor for Maya. It will run any code using maya.utils.executeInMainThread. 
    """

    def __init__(self, server: 'Server') -> None:
        super().__init__(server)

        try:
            import maya.utils
            self.executeInMainThreadWithResult: Callable[..., Any] = maya.utils.executeInMainThreadWithResult
            logger.success("Fetched maya.utils.executeInMainThreadWithResult")
        except:
            logger.error("Couldn't fetch maya.utils.executeInMainThreadWithResult")

    def execute(self, function_name: str, parameters_dict: Dict[str, Any]) -> None:
        parameters_dict.pop(Constants.module, None)
        function: Callable[..., Any] = self.server.get_function_by_name(function_name)

        try:
            return_value: Any = self.executeInMainThreadWithResult(function, **parameters_dict)
            success: bool = True
            logger.success(f"MayaExecutor executed {function}")
        except Exception as err:
            trace: str = str(traceback.format_exc())
            return_value = trace
            success = False
            logger.error(f"MayaExecutor couldn't execute {function}")
            logger.error(str(err))
            logger.error(trace)

        result_json: Dict[str, Any] = make_result_json(success, return_value, function_name)
        self.server.executor_reply = result_json


class BlenderExecutor(GenericMainThreadExecutor):
    """
    A specific MainThreadExecutor for Blender. It will schedule any code to be registered with
    bpy.app.timers, where it will run in the main UI thread of Blender. It uses an inner function
    that will wrap the actual code in order to get a proper result back and make sure we can wait
    until the code execution is done before we continue.
    """

    def __init__(self, server: 'Server') -> None:
        super().__init__(server)

        try:
            import bpy.app.timers
            self.register: Callable[[Callable[[], Optional[float]]], None] = bpy.app.timers.register
            logger.success("Fetched bpy.app.timers.register")
        except:
            logger.error("Couldn't fetch bpy.app.timers.register")

    def execute(self, function_name: str, parameters_dict: Dict[str, Any]) -> None:
        parameters_dict.pop(Constants.module, None)
        function: Callable[..., Any] = self.server.get_function_by_name(function_name)

        done_event: threading.Event = threading.Event()
        result: List[Optional[Any]] = [None]
        error: List[Optional[str]] = [None]

        def timer_function() -> None:
            try:
                logger.info(function)
                result[0] = function(**parameters_dict)
            except Exception as e:
                error[0] = str(e)
            finally:
                logger.info("we're done!")
                done_event.set()

            # Unregister timer
            return None

            # run the function in Blenders's main thread

        self.register(timer_function)
        done_event.wait()  # Wait until done_event is set(), then continue

        if error[0]:
            success: bool = False
            logger.error(f"BlenderExecutor couldn't execute {function}")
            result_json: Dict[str, Any] = make_result_json(success, error[0], function_name)
        else:
            success = True
            logger.success(f"BlenderExecutor executed {function}")
            result_json = make_result_json(success, result[0], function_name)
        self.server.executor_reply = result_json


class Server:
    """
    Main SkyHook server class

    There are 3 callbacks that you can hook into from the outside:
    ServerEvents.is_terminated: called when stop_listening() is called
    ServerEvents.exec_command: called when a non-server command is executed through the MainThreadExecutor
    ServerEvents.command: always called with the command name and parameter dictionary,
             whether the command was a non-server or server command
    """

    def __init__(
            self,
            host_program: Optional[str] = None,
            port: Optional[int] = None,
            load_modules: List[str] = [],
            use_main_thread_executor: bool = False,
            echo_response: bool = True,
            only_allow_localhost_connections: bool = True
    ) -> None:

        self.events: EventEmitter = EventEmitter()
        self.executor_reply: Optional[Dict[str, Any]] = None

        if port:
            self.port: int = port
        else:
            self.port = self.__get_host_program_port(host_program)

        self.server_address = "127.0.0.1" if only_allow_localhost_connections else "0.0.0.0"

        self.__host_program: Optional[str] = host_program
        self.__keep_running: bool = True
        self.__use_main_thread_executor: bool = use_main_thread_executor
        self.__http_server: Optional[HTTPServer] = None
        self.__echo_response: bool = echo_response
        self.__loaded_modules: List[types.ModuleType] = []
        self.__loaded_modules.append(core)

        for module_name in load_modules:
            if not self.hotload_module(module_name):  # first try to load it from the skyhook.modules package
                self.hotload_module(module_name,
                                    is_skyhook_module=False)  # should that fail, try again as a non skyhook.modules module

    def start_listening(self) -> None:
        """
        Creates a RequestHandler and starts the listening for incoming requests. Will continue to listen for requests
        until self.__keep_running is set to False

        :return: None
        """

        def handler(*args: Any) -> None:
            SkyHookHTTPRequestHandler(skyhook_server=self, *args)

        self.__http_server = HTTPServer((self.server_address, self.port), handler)
        logger.info(f"Started SkyHook on port: {self.port}")
        while self.__keep_running:
            self.__http_server.handle_request()
        logger.info("Shutting down server")
        self.__http_server.server_close()
        logger.info("Server shut down")

    def stop_listening(self) -> None:
        """
        Stops listening for incoming requests. Also emits the is_terminated event with "TERMINATED"

        :return: None
        """
        self.__keep_running = False
        if self.__http_server:
            self.__http_server.server_close()
        self.events.emit("is_terminated", "TERMINATED")

    def reload_modules(self) -> List[str]:
        """
        Reloads all the currently loaded modules. This can also be called remotely by sending
        ServerCommands.SKY_RELOAD_MODULES as the FunctionName.

        :return: List of reloaded module names
        """
        reload_module_names: List[str] = []

        for module in self.__loaded_modules:
            try:
                reload(module)
                reload_module_names.append(module.__name__)
            except:
                importlib.reload(module)
        return reload_module_names

    def hotload_module(self, module_name: Union[str, types.ModuleType], is_skyhook_module: bool = True) -> None:
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
                mod: types.ModuleType = importlib.import_module(f".modules.{module_name}", package="skyhook")
            else:
                mod = importlib.import_module(module_name)

            if not mod in self.__loaded_modules:
                self.__loaded_modules.append(mod)
                logger.info(f"Added {mod}")
                logger.info(self.__loaded_modules)
            return True

        except Exception as err:
            logger.error(f"Failed to hotload: {module_name}")
            logger.error(err)
            return False

    def unload_modules(self, module_name: str, is_skyhook_module: bool = True) -> None:
        """
        Removes a module from the server

        :param module_name: *string* name of the module you want to remove
        :param is_skyhook_module: *bool* set this to true if the module you want to remove is a skyhook module
        :return: None
        """
        if is_skyhook_module:
            full_name: str = "skyhook.modules." + module_name
        else:
            full_name = module_name
        for module in self.__loaded_modules:
            if module.__name__ == full_name:
                self.__loaded_modules.remove(module)

    def get_function_by_name(self, function_name: str, module_name: Optional[str] = None) -> Callable[..., Any]:
        """
        Tries to find a function by name.

        :param function_name: *string* name of the function you're looking for
        :param module_name: *string* name of the module to search in. If None, all modules are searched
        :return: the actual function that matches your name, or None
        """
        if module_name is not None:
            module = sys.modules.get(f".modules.{module_name}")
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

        # If no function is found, return a dummy function that raises an error
        def function_not_found(*args: Any, **kwargs: Any) -> None:
            raise ValueError(f"Function {function_name} not found")

        return function_not_found

    def filter_and_execute_function(self, function_name: str, parameters_dict: Dict[str, Any]) -> bytes:
        """
        This function decides whether or the function call should come from one of the loaded modules or from the server.
        Every server function should start with SKY_

        You shouldn't call this function directly.

        :param function_name: Name of the function to execute
        :param parameters_dict: Dictionary of parameters to pass to the function
        :return: JSON response as bytes
        """
        if function_name in dir(ServerCommands):
            result_json: Dict[str, Any] = self.__process_server_command(function_name, parameters_dict)
        else:
            result_json = self.__process_module_command(function_name, parameters_dict)

        self.executor_reply = None
        return json.dumps(result_json).encode()

    def __process_server_command(self, function_name: str, parameters_dict: Dict[str, Any] = {}) -> Dict[str, Any]:
        """
        Processes a command if the function in it was a server function.

        You shouldn't call this function directly

        :param function_name: Name of the server command to execute
        :param parameters_dict: Dictionary of parameters for the command
        :return: Result JSON dictionary
        """
        result_json: Dict[str, Any] = make_result_json(False, Errors.SERVER_COMMAND, None)

        if function_name == ServerCommands.SKY_SHUTDOWN:
            self.stop_listening()
            result_json = make_result_json(True, "Server offline", ServerCommands.SKY_SHUTDOWN)

        elif function_name == ServerCommands.SKY_LS:
            functions: List[str] = []
            for module in self.__loaded_modules:
                functions.extend(
                    [func for func in dir(module) if not "__" in func or isinstance(func, types.FunctionType)])
            result_json = make_result_json(True, functions, ServerCommands.SKY_LS)

        elif function_name == ServerCommands.SKY_RELOAD_MODULES:
            reloaded_modules: List[str] = self.reload_modules()
            result_json = make_result_json(True, reloaded_modules, ServerCommands.SKY_RELOAD_MODULES)

        elif function_name == ServerCommands.SKY_UNLOAD:
            modules: List[str] = parameters_dict.get(Constants.module, [])
            for module in modules:
                self.unload_modules(module)

            result_json = make_result_json(True, [m.__name__ for m in self.__loaded_modules], ServerCommands.SKY_UNLOAD)

        elif function_name == ServerCommands.SKY_FUNCTION_HELP:
            function_name_param: str = parameters_dict.get("function_name", "")
            function: Callable[..., Any] = self.get_function_by_name(function_name_param)
            arg_spec = inspect.getfullargspec(function)

            arg_spec_dict: Dict[str, Any] = {
                "function_name": function_name_param,
                "arguments": arg_spec.args
            }

            if arg_spec.varargs is not None:
                arg_spec_dict["packed_args"] = f"*{arg_spec.varargs}"
            if arg_spec.keywords is not None:
                arg_spec_dict["packed_kwargs"] = f"**{arg_spec.keywords}"

            result_json = make_result_json(True, arg_spec_dict, ServerCommands.SKY_FUNCTION_HELP)

        self.events.emit(ServerEvents.command, function_name, {})
        logger.success(f"Executed {function_name}")

        return result_json

    def __process_module_command(self, function_name: str, parameters_dict: Dict[str, Any], timeout: float = 10.0) -> Dict[str, Any]:
        """
        Processes a command if the function in it was a module function.

        You shouldn't call this function directly

        :param function_name: Name of the function to execute
        :param parameters_dict: Dictionary of parameters for the function
        :param timeout: Timeout in seconds for waiting for executor reply
        :return: Result JSON dictionary
        """
        if self.__use_main_thread_executor:
            logger.debug("Emitting exec_command event")
            self.events.emit(ServerEvents.exec_command, function_name, parameters_dict)
            start_time: float = time.time()

            while self.executor_reply is None:
                # wait for the executor to reply, just keep checking the time to see if we've waited longer
                # than timeout permits
                current_time: float = time.time()
                if current_time - start_time > timeout:
                    self.executor_reply = make_result_json(success=False, return_value=Errors.TIMEOUT,
                                                           command=function_name)
            return self.executor_reply

        module: Optional[str] = parameters_dict.get(Constants.module)
        parameters_dict.pop(Constants.module,
                            None)  # remove module from the parameters, otherwise it gets passed to the function
        function: Callable[..., Any] = self.get_function_by_name(function_name, module)

        try:
            return_value: Any = function(**parameters_dict)
            success: bool = True
            self.events.emit(ServerEvents.command, function_name, parameters_dict)
        except Exception as err:
            trace: str = str(traceback.format_exc())
            return_value = trace
            success = False

        result_json: Dict[str, Any] = make_result_json(success, return_value, function_name)
        return result_json

    def __get_host_program_port(self, host_program: Optional[str]) -> int:
        """
        Looks through the Constants.Ports class to try and find the port for the host program. If it can't, it will
        default to Constants.Ports.undefined

        You shouldn't call this function directly

        :param host_program: *string* name of the host program
        :return: Port number as integer
        """
        try:
            if host_program is not None:
                return getattr(Ports, host_program)
            return getattr(Ports, Constants.undefined)
        except Exception:
            return getattr(Ports, Constants.undefined)


class SkyHookHTTPRequestHandler(BaseHTTPRequestHandler):
    """
    The class that handles requests coming into the server. It holds a reference to the Server class, so
    it can call the Server functions after it has processed the request.
    """
    skyhook_server: Server

    def __init__(
            self,
            request: socket.socket,
            client_address: tuple,
            server: HTTPServer,
            skyhook_server: Optional[Server] = None,
            reply_with_auto_close: bool = True
    ) -> None:

        self.skyhook_server = skyhook_server
        self.reply_with_auto_close = reply_with_auto_close
        self.quiet = False
        super().__init__(request, client_address, server)

    def do_GET(self) -> None:
        """
        Handle a GET request, this would be just a browser requesting a particular url
        like: http://localhost:65500/%22echo_message%22&%7B%22message%22:%22Hooking%20into%20the%20Sky%22%7D
        """
        # browsers tend to send a GET for the favicon as well, which we don't care about
        if self.path == "/favicon.ico":
            return

        data: str = urllib.parse.unquote(self.path).lstrip("/")
        parts: List[str] = data.split("&")

        try:
            function: str = eval(parts[0])
            parameters: Dict[str, Any] = json.loads(parts[1])
        except NameError as err:
            logger.warning(f"Got a GET request that I don't know what to do with")
            logger.warning(f"Request was: GET {data}")
            logger.warning(f"Error is   : {err}")
            return

        command_response: bytes = self.skyhook_server.filter_and_execute_function(function, parameters)
        self.send_response_data("GET")
        self.wfile.write(bytes(f"{command_response}".encode("utf-8")))
        if self.reply_with_auto_close:
            # reply back to the browser with a javascript that will close the window (tab) it just opened
            self.wfile.write(bytes("<script type='text/javascript'>window.open('','_self').close();</script>".encode("utf-8")))

    def do_POST(self) -> None:
        """
        Handle a post request, expects a JSON object to be sent in the POST data
        """
        content_length: int = int(self.headers['Content-Length'])
        post_data: bytes = self.rfile.read(content_length)
        decoded_data: str = post_data.decode('utf-8')
        json_data: Dict[str, Any] = json.loads(decoded_data)

        function: str = json_data.get(Constants.function_name, "")
        parameters: Dict[str, Any] = json_data.get(Constants.parameters, {})

        command_response: bytes = self.skyhook_server.filter_and_execute_function(function, parameters)
        self.send_response_data("POST")
        self.wfile.write(command_response)

    def send_response_data(self, request_type: str) -> None:
        """
        Generates the response and appropriate headers to send back to the client

        :param request_type: *string* GET or POST
        """
        self.send_response(200)

        # Add CORS headers for all responses
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

        if request_type == "GET":
            self.send_header('Content-type', 'text/html')
        elif request_type == "POST":
            self.send_header('Content-type', 'application/json')
        else:
            pass
        self.end_headers()

    def do_OPTIONS(self) -> None:
        """
        Handle OPTIONS requests for CORS preflight
        """
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, fmt, *args):
        if not self.quiet:
            super().log_message(fmt, *args)


def port_in_use(port_number: int, host: str = "127.0.0.1", timeout: float = 0.125) -> bool:
    """
    Checks if a specific ports is already in use by a different process. Useful if you want to check if you can start
    a SkyHook server on a default port that might already be in use.

    :param port_number: Port you want to check
    :param host: Hostname, default is 127.0.0.1
    :param timeout: when the socket should time out
    :return: True if port is in use, False otherwise
    """
    sock: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    result: int = sock.connect_ex((host, port_number))
    if result == 0:
        return True
    return False


def make_result_json(success: bool, return_value: Any, command: str) -> Dict[str, Any]:
    """
    Little helper function to construct a json for the server to send back after a POST request

    :param success: Whether the command was successful
    :param return_value: The return value of the command
    :param command: The command that was executed
    :return: Dictionary with result information
    """
    result_json: Dict[str, Any] = {
        Results.time: datetime.now().strftime("%H:%M:%S"),
        Results.success: success,
        Results.return_value: return_value,
        Results.command: command
    }

    return result_json


def start_server_in_thread(
        host_program: str = "",
        port: Optional[int] = None,
        load_modules: List[str] = [],
        echo_response: bool = False,
        only_allow_localhost_connections: bool = True
) -> List[Optional[Union[threading.Thread, Server]]]:
    """
    Starts a server in a separate thread. 

    :param host_program: *string* name of the host program
    :param port: *int* port override
    :param load_modules: *list* modules to load
    :param echo_response: *bool* print the response the server is sending back
    :param only_allow_localhost_connections: *bool* if set to false, also allow connections from other clients on the network
    :return: *List* containing Thread and Server or None values if server couldn't start
    """
    if host_program != "":
        port = getattr(Ports, host_program)

    host = "127.0.0.1" if only_allow_localhost_connections else "0.0.0.0"
    if port_in_use(port, host):
        logger.error(f"Port {port} is already in use, can't start server")
        return [None, None]

    skyhook_server: Server = Server(host_program=host_program, port=port, load_modules=load_modules,
                                    echo_response=echo_response,
                                    only_allow_localhost_connections=only_allow_localhost_connections)

    def kill_thread_callback(message: str) -> None:
        logger.info(f"\nSkyhook server thread was killed with message {message}")

    skyhook_server.events.connect(ServerEvents.is_terminated, kill_thread_callback)

    thread: threading.Thread = threading.Thread(target=skyhook_server.start_listening)
    thread.daemon = True
    thread.start()

    return [thread, skyhook_server]


def start_executor_server_in_thread(
        host_program: str = "",
        port: Optional[int] = None,
        load_modules: List[str] = [],
        echo_response: bool = False,
        executor: Optional[GenericMainThreadExecutor] = None,
        executor_name: Optional[str] = None,
        only_allow_localhost_connections: bool = True
) -> List[Optional[Union[threading.Thread, GenericMainThreadExecutor, Server]]]:
    """
    Starts a server in a thread, but moves all executing functionality to a MainThreadExecutor object. Use this
    for a host program where executing code in a thread other than the main thread is not safe. Eg: Blender

    :param host_program: *string* name of the host program
    :param port: *int* port override
    :param load_modules: *list* modules to load
    :param echo_response: *bool* print the response the server is sending back
    :param executor: Optional executor instance to use
    :param executor_name: Name of an executor to use, for example "maya" or "blender"
    :param only_allow_localhost_connections: *bool* if set to false, also allow connections from other clients on the network
    :return: *List* containing Thread, MainThreadExecutor and Server or None values if server couldn't start
    """
    if host_program != "":
        port = getattr(Ports, host_program)

    if port is None:
        port = getattr(Ports, Constants.undefined)

    host = "127.0.0.1" if only_allow_localhost_connections else "0.0.0.0"
    if port_in_use(port, host):
        logger.error(f"Port {port} is already in use, can't start server")
        return [None, None, None]

    skyhook_server: Server = Server(host_program=host_program, port=port, load_modules=load_modules,
                                    use_main_thread_executor=True, echo_response=echo_response,
                                    only_allow_localhost_connections=only_allow_localhost_connections)

    executor_mapping: Dict[str, Type[GenericMainThreadExecutor]] = {
        HostPrograms.maya: MayaExecutor,
        HostPrograms.blender: BlenderExecutor,
    }

    # if we didn't specify an executor to use, figure out which one we should make
    if executor is None:
        executor_key: Optional[str] = None

        # executor_name > host_program > default
        if executor_name is not None:
            executor_key = executor_name
            logger.info(f"Using executor specified by name: {executor_name}")
        elif host_program:
            executor_key = host_program
            logger.info(f"Using executor based on host program: {host_program}")

        # we found which one to use in the mapping
        if executor_key in executor_mapping:
            executor_class = executor_mapping[executor_key]
            # make the executor
            executor = executor_class(skyhook_server)
            logger.info(f"Created {executor_class.__name__}")
        # we couldn't find one, make a GenericMainThreadExecutor
        else:
            logger.warning("No specific executor found, using GenericMainThreadExecutor")
            executor = GenericMainThreadExecutor(skyhook_server)

    # Connect the exec_command event to the executor's execute method
    skyhook_server.events.connect(ServerEvents.exec_command, executor.execute)

    def kill_thread_callback(message: str) -> None:
        logger.info("\nSkyhook server thread was killed")

    skyhook_server.events.connect("is_terminated", kill_thread_callback)

    # running the server on a separate thread
    thread: threading.Thread = threading.Thread(target=skyhook_server.start_listening)
    thread.daemon = True
    thread.start()

    return [thread, executor, skyhook_server]


def start_blocking_server(
        host_program: str = "",
        port: Optional[int] = None,
        load_modules: List[str] = [],
        echo_response: bool = False,
        only_allow_localhost_connections: bool = True
) -> Optional[Server]:
    """
    Starts a server in the main thread. This will block your application. Use this when you don't care about your
    application being locked up.

    :param host_program: *string* name of the host program
    :param port: *int* port override
    :param load_modules: *list* modules to load
    :param echo_response: *bool* print the response the server is sending back
    :param only_allow_localhost_connections: *bool* if set to false, also allow connections from other clients on the network
    :return: Server instance or None if server couldn't start
    """
    if host_program != "":
        port = getattr(Ports, host_program)

    if port is None:
        port = getattr(Ports, Constants.undefined)

    host = "127.0.0.1" if only_allow_localhost_connections else "0.0.0.0"
    if port_in_use(port, host):
        logger.error(f"Port {port} is already in use, can't start server")
        return None

    skyhook_server: Server = Server(host_program=host_program, port=port,
                                    load_modules=load_modules, echo_response=echo_response,
                                    only_allow_localhost_connections=only_allow_localhost_connections)
    skyhook_server.start_listening()
    return skyhook_server                