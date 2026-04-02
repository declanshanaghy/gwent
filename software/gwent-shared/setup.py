from setuptools import setup, find_packages

setup(
    name="gwent-shared",
    version="0.1.0",
    description="Shared utilities for Gwent Companion (TTS, constants)",
    packages=find_packages(),
    python_requires=">=3.6",
    install_requires=[
        "gtts",
        "elevenlabs",
        "openai",
        "pygame>=2.1.2",
        "pydub>=0.24.0",
        'audioop-lts>=0.2.1; python_version>="3.13"',
    ],
)
