#!/bin/bash

# Script to set and manage environment configuration
# Usage: source ./scripts/set_env.sh [development|staging|production]

# Check if the script is being sourced
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script must be sourced, not executed."
    echo "Usage: source ./scripts/set_env.sh [development|staging|production]"
    exit 1
fi

# Define color codes for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Default environment is development
ENV=${1:-development}

# Validate environment
if [[ ! "$ENV" =~ ^(development|staging|production)$ ]]; then
    echo -e "${RED}Error: Invalid environment. Choose development, staging, or production.${NC}"
    return 1
fi

# Set environment variables
export APP_ENV=$ENV

# Get script directory and project root
# Using a simpler approach that works for most shells when sourced
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Check for environment-specific .env file
ENV_FILE="$PROJECT_ROOT/.env.$ENV"

if [ -f "$ENV_FILE" ]; then
    echo -e "${GREEN}Loading environment from $ENV_FILE${NC}"

    # Export all environment variables from the file
    set -a
    source "$ENV_FILE"
    set +a

    echo -e "${GREEN}Successfully loaded environment variables from $ENV_FILE${NC}"
else
    echo -e "${YELLOW}Warning: $ENV_FILE not found. Creating from .env.example...${NC}"

    EXAMPLE_FILE="$PROJECT_ROOT/.env.example"
    if [ -f "$EXAMPLE_FILE" ]; then
        cp "$EXAMPLE_FILE" "$ENV_FILE"
        echo -e "${GREEN}Created $ENV_FILE from template.${NC}"
        echo -e "${PURPLE}Please update it with your configuration.${NC}"

        # Export all environment variables from the new file
        set -a
        source "$ENV_FILE"
        set +a

        echo -e "${GREEN}Successfully loaded environment variables from new $ENV_FILE${NC}"
    else
        echo -e "${RED}Error: .env.example not found at $EXAMPLE_FILE${NC}"
        return 1
    fi
fi

# Print current environment
echo -e "\n${GREEN}======= ENVIRONMENT SUMMARY =======${NC}"
echo -e "${GREEN}Environment:     ${YELLOW}$ENV${NC}"
echo -e "${GREEN}Project root:    ${YELLOW}$PROJECT_ROOT${NC}"
echo -e "${GREEN}Project name:    ${YELLOW}${PROJECT_NAME:-Not set}${NC}"
echo -e "${GREEN}API version:     ${YELLOW}${VERSION:-Not set}${NC}"

# Show only the part after @ for database URL (for security)
if [[ -n "$POSTGRES_URL" && "$POSTGRES_URL" == *"@"* ]]; then
    DB_DISPLAY=$(echo "$POSTGRES_URL" | sed 's/.*@/@/')
    echo -e "${GREEN}Database URL:    ${YELLOW}*********$DB_DISPLAY${NC}"
else
    echo -e "${GREEN}Database URL:    ${YELLOW}${POSTGRES_URL:-Not set}${NC}"
fi

echo -e "${GREEN}LLM model:       ${YELLOW}${LLM_MODEL:-Not set}${NC}"
echo -e "${GREEN}Log level:       ${YELLOW}${LOG_LEVEL:-Not set}${NC}"
echo -e "${GREEN}Debug mode:      ${YELLOW}${DEBUG:-Not set}${NC}"

# Create helper functions
start_app() {
    echo -e "${GREEN}Starting application in $ENV environment...${NC}"
    cd "$PROJECT_ROOT" && uvicorn app.main:app --reload --port 8000
}

# Define the function for use in the shell (handle both bash and zsh)
if [[ -n "$BASH_VERSION" ]]; then
    export -f start_app
elif [[ -n "$ZSH_VERSION" ]]; then
    # For ZSH, we redefine the function (no export -f)
    function start_app() {
        echo -e "${GREEN}Starting application in $ENV environment...${NC}"
        cd "$PROJECT_ROOT" && uvicorn app.main:app --reload --port 8000
    }
else
    echo -e "${YELLOW}Warning: Unsupported shell. Using fallback method.${NC}"
    # No function export for other shells
fi

# Print help message
echo -e "\n${GREEN}Available commands:${NC}"
echo -e "  ${YELLOW}start_app${NC} - Start the application in $ENV environment"

# Create aliases for environments
alias dev_env="source '$SCRIPT_DIR/set_env.sh' development"
alias stage_env="source '$SCRIPT_DIR/set_env.sh' staging"
alias prod_env="source '$SCRIPT_DIR/set_env.sh' production"

echo -e "  ${YELLOW}dev_env${NC} - Switch to development environment"
echo -e "  ${YELLOW}stage_env${NC} - Switch to staging environment"
echo -e "  ${YELLOW}prod_env${NC} - Switch to production environment"
