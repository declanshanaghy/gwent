from setuptools import setup, find_packages

setup(
    name="gwent-tui",
    version="0.1.0",
    description="Live terminal dashboard for Gwent Companion",
    packages=find_packages(),
    python_requires=">=3.6",
    install_requires=[
        "paho-mqtt>=2.1.0",
        "rich>=13.3.0",
    ],
    entry_points={
        "console_scripts": [
            "gwent-tui=gwent_tui.app:main",
        ],
    },
)
