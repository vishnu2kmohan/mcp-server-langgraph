"""Setup configuration for MCP Server with LangGraph"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements-pinned.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="mcp-server-langgraph",
    version="1.0.0",
    author="MCP Server with LangGraph Contributors",
    author_email="maintainers@example.com",
    description="Production-ready MCP server with LangGraph, OpenFGA, and multi-LLM support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/vishnu2kmohan/mcp_server_langgraph",
    packages=find_packages(exclude=["tests", "tests.*", "examples", "examples.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.10,<3.13",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "pytest-asyncio>=0.23.3",
            "pytest-cov>=4.1.0",
            "black>=24.1.1",
            "flake8>=7.0.0",
            "mypy>=1.8.0",
            "isort>=5.13.2",
            "bandit>=1.7.6",
        ],
        "test": [
            "pytest>=8.0.0",
            "pytest-asyncio>=0.23.3",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.12.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "mcp-server=mcp_server:main",
            "mcp-server-http=mcp_server_streamable:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml", "*.json", "*.md"],
    },
    project_urls={
        "Bug Reports": "https://github.com/vishnu2kmohan/mcp_server_langgraph/issues",
        "Source": "https://github.com/vishnu2kmohan/mcp_server_langgraph",
        "Documentation": "https://github.com/vishnu2kmohan/mcp_server_langgraph/blob/main/README.md",
    },
)
