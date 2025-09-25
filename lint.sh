#!/bin/bash

# Linting and formatting script for the Raspberry Pi Video Recorder project

echo "🔍 Running Ruff linter..."
.venv/bin/ruff check . --fix

echo ""
echo "📐 Running isort (import sorting)..."
.venv/bin/isort .

echo ""
echo "🎨 Running Black (code formatting)..."
.venv/bin/black .

echo ""
echo "🔬 Running mypy (type checking)..."
.venv/bin/mypy . --ignore-missing-imports

echo ""
echo "✅ All linting and formatting completed!"
