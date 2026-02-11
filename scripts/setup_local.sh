#!/bin/bash
# setup_local.sh - One-command local setup for CryptoLake
set -e

echo "🏔️ CryptoLake — Local Setup"
echo "=========================="

# Check prerequisites
echo "Checking prerequisites..."
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 is required but not installed."; exit 1; }

# Copy .env if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Created .env from .env.example"
fi

# Create Python virtual environment
if [ ! -d .venv ]; then
    python3 -m venv .venv
    echo "✅ Created virtual environment"
fi

# Activate and install dependencies
source .venv/bin/activate
pip install -e ".[dev]" --quiet
echo "✅ Installed Python dependencies"

# Start Docker services
echo "🚀 Starting Docker services..."
make up

echo ""
echo "🎉 Setup complete! CryptoLake is ready."
echo "   Run 'source .venv/bin/activate' to activate the virtual environment."
