#!/bin/bash
set -e

# Setup for deepagents
echo "--- Setting up and testing deepagents ---"
cd libs/deepagents
uv venv -p python3.12 --clear
source .venv/bin/activate
uv pip install -e .
uv pip install pytest pytest-cov pytest-xdist ruff mypy pytest-asyncio langchain-openai
pytest
deactivate
cd ../..

# Setup for deepagents-cli
echo "--- Setting up and testing deepagents-cli ---"
cd libs/deepagents-cli
uv venv -p python3.12 --clear
source .venv/bin/activate
uv pip install -e .
uv pip install pytest pytest-asyncio pytest-cov pytest-mock pytest-socket pytest-timeout responses ruff
pytest
deactivate
cd ../..
