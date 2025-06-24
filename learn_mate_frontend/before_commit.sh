#!/bin/bash

# Before commit hook script for learn_mate_frontend
# This script runs all necessary checks before committing code

set -e  # Exit on error

echo "🔍 Running pre-commit checks for frontend..."
echo "==========================================="

# 1. Run lint check
echo "🔎 Running lint check..."
if pnpm lint; then
    echo "✅ Lint check passed"
else
    echo "⚠️  Lint check found issues, attempting auto-fix..."
    pnpm lint:fix
    echo "✅ Lint issues fixed"
fi
echo ""

# 2. Run type check
echo "📝 Running type check..."
if pnpm type-check; then
    echo "✅ Type check passed"
else
    echo "❌ Type check failed. Please fix the type errors above."
    exit 1
fi
echo ""

# 3. Format code
echo "💅 Formatting code..."
pnpm format
echo "✅ Code formatting completed"
echo ""

# 4. Build project
echo "🏗️  Building project..."
if pnpm build; then
    echo "✅ Build completed successfully"
else
    echo "❌ Build failed. Please fix the build errors above."
    exit 1
fi
echo ""

echo "==========================================="
echo "✅ All pre-commit checks passed!"
echo "You can now commit your changes."