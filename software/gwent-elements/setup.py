#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name="gwent-elements",
    version="0.1.0",
    description="Hardware interface elements for the Gwent project",
    author="Declan Shanaghy",
    author_email="declanshanaghy@gmail.com",
    packages=find_packages(),
    install_requires=[
        # CircuitPython/Blinka dependencies
        "adafruit-blinka",
        "adafruit-circuitpython-busdevice",
        "adafruit-circuitpython-ssd1305",
        "adafruit-circuitpython-ssd1306",
        "adafruit-circuitpython-is31fl3731",
        "adafruit-circuitpython-framebuf",
        
        # Display dependencies
        "pillow",
        "luma.oled",
        "luma.core",
        
        # Communication dependencies
        "asyncio-mqtt",
        "aioredis",
        "python-dotenv",
        
        # Sensor dependencies
        "sparkfun-qwiic-tca9548a",
    ],
    dependency_links=[
        # Input dependencies from GitHub
        "git+https://github.com/guyc/py-gaugette.git#egg=gaugette",
    ],
    python_requires=">=3.7",
    include_package_data=True,
    package_data={
        "gwent_elements": ["fonts/*"],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
)