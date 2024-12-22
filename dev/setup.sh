#!/usr/bin/env bash
set -e

# ------------------------------------------------------------------------------
# 1. Create a fresh Python virtual environment (named "nsql_env")
# ------------------------------------------------------------------------------
echo "Creating Python virtual environment..."
python3 -m venv nsql_env

# Activate the environment
source nsql_env/bin/activate

# ------------------------------------------------------------------------------
# 2. Install dependencies
# ------------------------------------------------------------------------------
echo "Installing required Python packages..."
pip install --upgrade pip
pip install "transformers==4.35.2" torch safetensors accelerate


