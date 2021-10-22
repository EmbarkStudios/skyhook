import importlib
from .. import client


def is_online():
    """
    Being able to call this function means the server is online and able to handle requests.

    :return: True
    """
    return True

def echo_message(message):
    print(message)
    return "I printed: %s" % message


def run_python_script(script_path):
    import runpy
    runpy.run_path(script_path, init_globals=globals(), run_name="__main__")
