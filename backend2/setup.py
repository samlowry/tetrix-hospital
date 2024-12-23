from setuptools import setup, find_packages

setup(
    name="tetrix-hospital-bot",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "alembic",
        "aiohttp",
        "asyncpg",
    ],
) 