import setuptools

with open("../../README.md", "r") as fh:
    long_description = fh.read()

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
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache 2",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7.3',
    install_requires=[
        'aioconsole==0.2.0',
        'adafruit-circuitpython-is31fl3731==2.6.3',
        'adafruit-circuitpython-framebuf==1.3.2',
        'asyncio-mqtt==0.5.0',
        'gaugette==1.2',
        'gTTS==2.1.1',
        'jsonschema==3.2.0',
        'pygame==1.9.6',
        'pydub==0.24.0',
        'sparkfun-qwiic-i2c==0.9.11',
        'mfrc522==0.0.9',
        'websockets==8.1',
    ],
    entry_points={
        'console_scripts': [
            'gwent=gwent.game.main:run',
            'novigrad=gwent.novigrad.server:run',
            'write_card=gwent.game.poc:write_card',
            'read_card=gwent.game.poc:read_card',
        ],
    }
)
