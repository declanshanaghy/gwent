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
        'mfrc522==0.0.7',
        'wiringpi==2.60.0',
        'websockets==8.1',
    ],
    entry_points={
        'console_scripts': [
            'gwent-game=game.main:run',
            'gwent-server=server.async:run',
        ],
    }
)
