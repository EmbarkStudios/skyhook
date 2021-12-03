import os
import datetime

class Status:
    SUCCESS = "Success"
    WARNING = "Warning"
    INFO    = "Info"
    ERROR   = "Error"
    DEBUG   = "Debug"


class Logger(object):
    def __init__(self, file_path=None, print_to_screen=True):
        super(Logger, self).__init__()

        self.file_path = file_path if file_path is not None else os.path.join(os.path.expanduser("~"), "skyhook.log")
        self.__print_to_screen = print_to_screen

        self.debug("\n\n====================== NEW LOG ======================", print_to_screen=False)

    def success(self, message, print_to_screen=True):
        self.__add_to_log(Status.SUCCESS, message, print_to_screen)

    def warning(self, message, print_to_screen=True):
        self.__add_to_log(Status.WARNING, message, print_to_screen)

    def info(self, message, print_to_screen=True):
        self.__add_to_log(Status.INFO, message, print_to_screen)

    def error(self, message, print_to_screen=True):
        self.__add_to_log(Status.ERROR, message, print_to_screen)

    def debug(self, message, print_to_screen=True):
        self.__add_to_log(Status.DEBUG, message, print_to_screen)

    def __add_to_log(self, status, message, print_to_screen):
        time = datetime.datetime.now().strftime("%Y/%m/%d-%H:%M:%S")
        line = "SKYHOOK [%s] | %s | %s" % (time, status, message)

        with open(self.file_path, "a") as out_file:
            out_file.write(line + "\n")

        if print_to_screen:
            print(line)
