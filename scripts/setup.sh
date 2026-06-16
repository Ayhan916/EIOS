#!/usr/bin/env bash
# EIOS Development Environment Bootstrap
# Run once from the repository root: bash scripts/setup.sh

set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/backend"

echo "=== EIOS Development Setup ==="

# Check for Homebrew
if ! command -v brew &>/dev/null; then
  echo "ERROR: Homebrew is required. Install at https://brew.sh"
  exit 1
fi

# Install Python 3.12 if not present
if ! command -v python3.12 &>/dev/null; then
  echo "Installing Python 3.12..."
  brew install python@3.12
fi
echo "Python: $(python3.12 --version)"

# Install uv if not present
if ! command -v uv &>/dev/null; then
  echo "Installing uv..."
  brew install uv
fi
echo "uv: $(uv --version)"

# Install backend dependencies
echo "Installing backend dependencies..."
cd "$BACKEND_DIR"
uv sync --dev

# Create .env from example if not present
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created backend/.env from .env.example — update SECRET_KEY before production use."
fi

# Verify tests pass
echo "Running domain layer tests..."
uv run pytest tests/unit/ -v --tb=short

echo ""
echo "=== Setup complete ==="
echo "Start the database: docker compose up -d"
echo "Run tests:          cd backend && uv run pytest"
