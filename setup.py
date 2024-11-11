from setuptools import setup, find_packages

setup(
    name="client_for3party",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "aiohttp",
        "pydantic",
    ],
    python_requires=">=3.10",
    include_package_data=True,
    zip_safe=False,
    description="A simple, reliable, and easy-to-debug unified client for third-party APIs",
    author="Erlock Lewis",
    author_email="oerlock@gmail.com",
    url="https://github.com/oerlock/client_for3party",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
