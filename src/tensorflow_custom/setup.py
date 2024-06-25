from setuptools import setup, find_packages

setup(
    name="tensorflow",
    version="2.7.3",
    packages=find_packages("./tensorflow_custom"),
    author="Niro Amerasinghe",
    author_email="niroam@amazon.com",
    description="A custom stub package to override the tensorflow requirement in this project that is not required. See project README for more details",
    long_description="A custom I/O package with additional functionality.",
    url="https://github.com/aws-samples/mixed-media-portal-on-aws/src/tensorflow_custom",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
