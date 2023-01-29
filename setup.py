from setuptools import setup, find_packages


setup(
    name="guiltysync",
    version="0.5.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "Click",
        "requests",
        "fastapi",
        "uvicorn"
    ],
    entry_points={
        "console_scripts": [
            "guiltysync = guiltysync.scripts:cli",
        ],
    },
)
