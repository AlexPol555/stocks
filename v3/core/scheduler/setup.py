"""Setup script for the task scheduler module."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="task-scheduler",
    version="1.0.0",
    author="Trading System Team",
    author_email="team@tradingsystem.com",
    description="Task scheduler for automated trading system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/trading-system",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Office/Business :: Financial :: Investment",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-asyncio>=0.18.0",
            "black>=21.0.0",
            "flake8>=3.9.0",
            "mypy>=0.910",
        ],
        "streamlit": [
            "streamlit>=1.20.0",
            "plotly>=5.0.0",
        ],
        "production": [
            "gunicorn>=20.0.0",
            "uvicorn>=0.15.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "scheduler=core.scheduler.__main__:main",
            "scheduler-cli=core.scheduler.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "core.scheduler": ["*.md", "*.txt", "*.yml", "*.yaml"],
    },
    zip_safe=False,
)
