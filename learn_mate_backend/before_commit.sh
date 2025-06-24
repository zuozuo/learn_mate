#!/bin/bash

# Before commit hook script for learn_mate_backend
# This script runs all necessary checks before committing code

set -e  # Exit on error

echo "🔍 Running pre-commit checks..."
echo "================================"

# 1. Format code
echo "📝 Formatting code with ruff..."
ruff format .
echo "✅ Code formatting completed"
echo ""

# 2. Run linter
echo "🔎 Running linter..."
if ruff check . --fix; then
    echo "✅ Linting passed"
else
    echo "❌ Linting failed. Please fix the errors above."
    exit 1
fi
echo ""

# 3. Run tests
echo "🧪 Running tests..."
if ./run_tests.sh; then
    echo "✅ All tests passed"
else
    echo "❌ Tests failed. Please fix the failing tests."
    exit 1
fi
echo ""

echo "================================"
echo "✅ All pre-commit checks passed!"
echo "You can now commit your changes."