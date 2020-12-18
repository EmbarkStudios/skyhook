import sys
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

if sys.version.major == 2:
    requires = ['requests', 'pyside', 'websockets']
else:
    requires = ['requests', 'pyside2', 'websockets']

setuptools.setup(
    name="skyhook",
    version="1.0.0",
    author="Niels Vaes",
    author_email="niels.vaes@embark-studios.com",
    description="Engine and DCC communication system",
    long_description="Engine and DCC communication system",
    long_description_content_type="text/markdown",
    url="https://github.com/EmbarkStudios/skyhook",
    install_requires=requires,
    packages=setuptools.find_packages(),
    classifiers=[
        "Operating System :: OS Independent",
    ]
)