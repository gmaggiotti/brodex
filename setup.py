from setuptools import setup, find_packages

setup(
    name="brodex",
    version="0.1.0",
    description="AI coding assistant powered by Groq. Explore code, search web, write and fix code.",
    author="brodex",
    packages=find_packages(),
    install_requires=[
        "groq>=0.4.1",
        "click>=8.1.0",
        "rich>=13.7.0",
        "httpx>=0.25.0",
        "beautifulsoup4>=4.12.0",
        "prompt_toolkit>=3.0.0",
        "lxml>=4.9.0",
    ],
    entry_points={
        "console_scripts": [
            "brodex=aicode.main:cli",
        ],
    },
)
