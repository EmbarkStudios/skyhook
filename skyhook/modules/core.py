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