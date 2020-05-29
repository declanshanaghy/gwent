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
        'gTTS==2.1.1',
        'pydub==0.24.0',
        'rx==3.1.0',
        'simpleaudio==1.0.4',
        'jsonschema==3.2.0',
        # 'mfrc522==0.0.9',
        'websockets==8.1',
    ],
    entry_points={
        'console_scripts': [
            'gwent=gwent.game.main:run',
            'novigrad=gwent.novigrad.server:run',
            'mfrc522_read_all_sectors=gwent.hal.mfrc522_entrypoints:mfrc522_read_all_sectors',
            'mfrc522_write_all_sectors=gwent.hal.mfrc522_entrypoints:mfrc522_write_all_sectors',
            'write_card=gwent.cards.util:write_card',
            'read_card=gwent.cards.util:read_card',
        ],
    }
)
