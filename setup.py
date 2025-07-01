import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

# any data files that match this pattern will be included
data_files_to_include = ["*.png"]

setuptools.setup(
    name="skyhook",
    version="3.0.1",
    author="Niels Vaes",
    author_email="nielsvaes@gmail.com",
    description="Engine and DCC communication system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/EmbarkStudios/skyhook",
    install_requires=['requests'],
    packages=setuptools.find_packages(),
    package_data={
        "": data_files_to_include,
    },
    python_requires='>=3.6',  
    classifiers=[
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "License :: OSI Approved :: MIT License",
        "Development Status :: 5 - Production/Stable",
    ],
    license="MIT",
    keywords='engine dcc communication system',
    project_urls={
        'Homepage': 'https://github.com/EmbarkStudios/skyhook',
        'Documentation': 'https://github.com/EmbarkStudios/skyhook/wiki',
        'Issue Tracker': 'https://github.com/EmbarkStudios/skyhook/issues',
    },
)