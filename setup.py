"""Setup configuration for LangGraph MCP Agent"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements-pinned.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="langgraph-mcp-agent",
    version="1.0.0",
    author="LangGraph MCP Agent Contributors",
    author_email="maintainers@example.com",
    description="Production-ready LangGraph agent with MCP, OpenFGA, and multi-LLM support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/YOUR_ORG/langgraph_mcp_agent",
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
    python_requires=">=3.10",
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
            "langgraph-mcp=mcp_server:main",
            "langgraph-mcp-http=mcp_server_streamable:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml", "*.json", "*.md"],
    },
    project_urls={
        "Bug Reports": "https://github.com/YOUR_ORG/langgraph_mcp_agent/issues",
        "Source": "https://github.com/YOUR_ORG/langgraph_mcp_agent",
        "Documentation": "https://github.com/YOUR_ORG/langgraph_mcp_agent/blob/main/README.md",
    },
)
