import sys
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

# any data files that match this pattern will be included
data_files_to_include = ["*.png"]

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
    version="2.2.4",
    author="Niels Vaes",
    author_email="niels.vaes@embark-studios.com",
    description="Engine and DCC communication system",
    long_description="Engine and DCC communication system",
    long_description_content_type="text/markdown",
    url="https://github.com/EmbarkStudios/skyhook",
    install_requires=requires,
    packages=setuptools.find_packages(),
    package_data={
        "": data_files_to_include,
    },
    classifiers=[
        "Operating System :: OS Independent",
    ]
)