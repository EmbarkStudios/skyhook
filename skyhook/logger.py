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

        self.debug("\n\n====================== NEW LOG ======================")

    def success(self, message):
        self.__add_to_log(Status.SUCCESS, message)

    def warning(self, message):
        self.__add_to_log(Status.WARNING, message)

    def info(self, message):
        self.__add_to_log(Status.INFO, message)

    def error(self, message):
        self.__add_to_log(Status.ERROR, message)

    def debug(self, message):
        self.__add_to_log(Status.DEBUG, message)

    def __add_to_log(self, status, message):
        time = datetime.datetime.now().strftime("%Y/%m/%d-%H:%M:%S")
        line = "[%s] | %s | %s" % (time, status, message)

        with open(self.file_path, "a") as out_file:
            out_file.write(line + "\n")

        if self.__print_to_screen:
            print(line)
