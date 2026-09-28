from setuptools import setup, find_packages

setup(
    name="hitesh-fastapi-starter",
    version="2.0.1",
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "hitesh-fastapi-starter=fastapi_starter.generator:create_project_cli",
            "fastapi-starter=fastapi_starter.generator:create_project_cli",
        ],
    },
)
