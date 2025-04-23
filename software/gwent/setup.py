import setuptools
import os

# Use a default long description if README.md is not found
try:
    with open(os.path.join(os.path.dirname(__file__), "README.md"), "r") as fh:
        long_description = fh.read()
except FileNotFoundError:
    long_description = "Gwent - Electronic board game"

setuptools.setup(
    name="gwent",
    version="0.0.1",
    author="Declan & Dylan Shanaghy",
    author_email="declan@shananghy.com",
    description="Electronic gwent board game",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/declanshanaghy/gwent",
    packages=setuptools.find_packages(),
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache 2",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6.11',
    setup_requires=['wheel'],
    install_requires=[
        'Adafruit-PlatformDetect==2.15.0',   # due to https://github.com/home-assistant/core/issues/40192
        'aioconsole==0.2.0',
        'adafruit-blinka==4.9.0',
        'adafruit-circuitpython-lis3dh==5.1.6',
        'adafruit-circuitpython-is31fl3731==2.6.3',
        'adafruit-circuitpython-framebuf==1.3.2',
        'adafruit-circuitpython-ssd1305==1.3.3',
        'asyncio-mqtt==0.5.0',
        'gTTS==2.2.4',
        'gpiozero>=1.6.2',
        'jsonschema==3.2.0',
        'luma.oled==3.8.1',
        'pydub==0.24.0',
        'rpi-lgpio>=0.1.0',  # Replacement for RPi.GPIO using lgpio
        'sparkfun-qwiic-tca9548a==0.9.0',
        'websockets==8.1',
        # 'mfrc522',
        # pygame is installed via apt-get on Raspberry Pi
        # 'pygame==2.1.2',
    ],
    entry_points={
        'console_scripts': [
            'gwent=gwent.game.main:run',
            'novigrad=gwent.novigrad.server:run',
            'rotary_rawgpio=gwent.poc.rotary_rawgpio:run',
            'rotary_gpiozero=gwent.poc.rotary_gpiozero:run'
        ],
    }
)
