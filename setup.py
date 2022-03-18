import sys
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

if sys.version_info.major == 2:
    try:
        import PySide
        requires = ['requests']
    except:
        requires = ['requests', 'pyside']
else:
    try:
        import PySide2
        requires = ['requests']
    except:
        requires = ['requests', 'pyside2']

setuptools.setup(
    name="skyhook",
    version="2.2.1",
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