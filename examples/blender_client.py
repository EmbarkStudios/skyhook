from skyhook.client import BlenderClient
from skyhook.modules import blender
from skyhook.modules import core
from skyhook import ServerCommands

# Make the client
client = BlenderClient()

# Let's make a cube using the blender module
client.execute(blender.make_cube)

# Let's print something using the default core module
client.execute(core.echo_message, parameters={"message": "Hi there, Blender!"})

# Let's shut the server down
client.execute(ServerCommands.SKY_SHUTDOWN)