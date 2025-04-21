import setuptools
import os

# Get the directory where setup.py is located
here = os.path.abspath(os.path.dirname(__file__))

# Get the project root directory (two levels up)
project_root = os.path.abspath(os.path.join(here, "../.."))

# Read the README.md file from the project root
try:
    with open(os.path.join(project_root, "README.md"), "r") as fh:
        long_description = fh.read()
except FileNotFoundError:
    long_description = "Electronic Gwent board game"

setuptools.setup(
    name="gwent",
    version="0.0.1",
    author="Declan & Dylan Shanaghy",
    author_email="declan@shanaghy.com",
    description="Electronic Gwent board game",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/declanshanaghy/gwent",
    packages=setuptools.find_packages(),
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6.11',
    setup_requires=['wheel'],
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
        ],
    },
    install_requires=[
        # Core dependencies
        'RPi.GPIO>=0.7.0',
        'gpiozero>=1.6.2',
        'lgpio>=0.1.0',  # Required for LGPIOFactory in gpiozero
        'pigpio>=1.78',  # Required for PiGPIOFactory in gpiozero
        
        # Adafruit libraries
        'Adafruit-Blinka>=6.0.0',
        'adafruit-circuitpython-busdevice',
        'adafruit-circuitpython-is31fl3731>=2.6.3',
        'adafruit-circuitpython-framebuf>=1.3.2',
        'adafruit-circuitpython-ssd1305>=1.3.3',
        'adafruit-circuitpython-ssd1306',
        
        # Display libraries
        'luma.oled>=3.8.1',
        'luma.core',
        'pillow',
        
        # RFID libraries
        'mfrc522-python==0.0.7',
        
        # Input libraries
        'gaugette>=1.2',
        
        # I2C multiplexer
        'sparkfun-qwiic-tca9548a>=0.9.0',
        
        # Audio libraries
        'pygame>=2.1.2',
        'gTTS>=2.2.4',
        'pydub>=0.24.0',
        
        # Utility libraries
        'jsonschema>=3.2.0',
        'python-dotenv>=0.19.0',
        'python-json-logger==3.3.0',
        'watchdog>=2.1.0',  # For monitoring file changes
        
        # Performance monitoring
        'psutil>=5.9.0',  # For monitoring CPU and memory usage
    ],
    entry_points={
        'console_scripts': [
            'gwent=gwent.game.main:main',
            'read_card=gwent.game.card_tools:read_card',
            'write_card=gwent.game.card_tools:write_card',
        ],
    }
)