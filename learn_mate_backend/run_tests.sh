#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Running API Tests for Learn Mate Backend${NC}"
echo "========================================"

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
pytest tests/test_repositories.py tests/test_services.py -v -m "not integration"

echo -e "\n${YELLOW}Running API Tests...${NC}"
pytest tests/api/v1/ -v

echo -e "\n${YELLOW}Running All Tests with Coverage...${NC}"
pytest --cov=app --cov-report=term-missing --cov-report=html

# Check if tests passed
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✓ All tests passed!${NC}"
    echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
else
    echo -e "\n${RED}✗ Some tests failed!${NC}"
    exit 1
fi