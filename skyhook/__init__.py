from .logger import Logger
logger = Logger()

from . import modules
from . import constants
from . import client
try:
    from . import server
except:
    logger.warning("Server import failed, so it won't be available in this instance")

from .constants import *