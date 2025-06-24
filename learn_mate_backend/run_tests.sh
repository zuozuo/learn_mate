#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Running API Tests for Learn Mate Backend${NC}"
echo "========================================"

# Set test environment
export ENVIRONMENT=test
export ENV_FILE=.env.test

# Unset proxy environment variables to avoid SOCKS proxy issues
unset http_proxy
unset https_proxy
unset HTTP_PROXY
unset HTTPS_PROXY
unset all_proxy
unset ALL_PROXY

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Install test dependencies if needed
echo -e "${YELLOW}Installing test dependencies...${NC}"
pip install -q pytest pytest-asyncio pytest-cov pytest-mock

# Run different test suites
echo -e "\n${YELLOW}Running Unit Tests...${NC}"
PYTHONPATH=. pytest tests/test_repositories.py tests/test_services.py -v -m "not integration" --tb=short

echo -e "\n${YELLOW}Running API Tests...${NC}"
PYTHONPATH=. pytest tests/api/v1/ -v --tb=short

echo -e "\n${YELLOW}Running Integration Tests...${NC}"
PYTHONPATH=. pytest tests/test_integration.py -v --tb=short

echo -e "\n${YELLOW}Running All Tests...${NC}"
PYTHONPATH=. pytest -v --tb=short

# Check if tests passed
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✓ All tests passed!${NC}"
    echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
else
    echo -e "\n${RED}✗ Some tests failed!${NC}"
    exit 1
fi