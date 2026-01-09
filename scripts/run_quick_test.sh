#!/bin/bash
# QBench Quick Test Script
# Runs a small subset of scenarios for quick validation

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
SCENARIOS="2"
SEEDS="1"
PARALLEL="1"
VERBOSE=""
OUTPUT=""
AGENT=""
AGENT_URL=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --agent)
            AGENT="$2"
            shift 2
            ;;
        --agent-url)
            AGENT_URL="$2"
            shift 2
            ;;
        --scenarios)
            SCENARIOS="$2"
            shift 2
            ;;
        --seeds)
            SEEDS="$2"
            shift 2
            ;;
        --parallel)
            PARALLEL="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE="--verbose"
            shift
            ;;
        --output)
            OUTPUT="--output $2"
            shift 2
            ;;
        --help|-h)
            echo "QBench Quick Test Script"
            echo ""
            echo "Usage:"
            echo "  Interactive:  ./scripts/run_quick_test.sh"
            echo "  Standalone:   ./scripts/run_quick_test.sh --agent <module.class>"
            echo "  Remote:       ./scripts/run_quick_test.sh --agent-url <url>"
            echo ""
            echo "Options:"
            echo "  --scenarios N      Number of scenarios (default: 2)"
            echo "  --seeds LIST       Comma-separated seed list (default: 1)"
            echo "  --parallel N       Parallel workers (default: 1)"
            echo "  --verbose          Show detailed logs"
            echo "  --output FILE      Output file path"
            echo ""
            echo "Examples:"
            echo "  ./scripts/run_quick_test.sh --agent examples.standalone.agent.GPT52Agent"
            echo "  ./scripts/run_quick_test.sh --agent-url http://localhost:9019 --scenarios 5"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Print header
echo ""
echo "=============================================="
echo "QBench Quick Test"
echo "=============================================="
echo ""

# Interactive mode if no agent specified
if [[ -z "$AGENT" && -z "$AGENT_URL" ]]; then
    echo -e "${BLUE}No agent specified. Entering interactive mode...${NC}"
    echo ""
    echo "Choose evaluation mode:"
    echo "  1) Standalone (Python agent class)"
    echo "  2) Remote (HTTP/A2A agent URL)"
    echo ""
    read -p "Selection [1-2]: " mode_selection

    case $mode_selection in
        1)
            echo ""
            echo -e "${BLUE}Standalone Mode${NC}"
            echo "Enter the Python module path to your agent class."
            echo "Example: examples.standalone.agent.GPT52Agent"
            echo ""
            read -p "Agent module path: " AGENT
            if [[ -z "$AGENT" ]]; then
                echo -e "${RED}Error: Agent module path cannot be empty${NC}"
                exit 1
            fi
            ;;
        2)
            echo ""
            echo -e "${BLUE}Remote Mode${NC}"
            echo "Enter the URL where your agent is running."
            echo ""
            read -p "Agent URL (default: http://localhost:9019): " AGENT_URL
            if [[ -z "$AGENT_URL" ]]; then
                AGENT_URL="http://localhost:9019"
            fi

            echo ""
            echo -e "${YELLOW}⚠️  Make sure your agent is running at: $AGENT_URL${NC}"
            echo ""
            read -p "Is your agent running? [y/N]: " agent_running
            if [[ ! $agent_running =~ ^[Yy]$ ]]; then
                echo ""
                echo "Please start your agent first, then run this script again."
                echo ""
                echo "Example:"
                echo "  python examples/agentbeats/gpt52_purple_agent.py"
                echo ""
                exit 0
            fi
            ;;
        *)
            echo -e "${RED}Invalid selection${NC}"
            exit 1
            ;;
    esac
fi

# Show configuration
echo ""
echo "Configuration:"
echo "  Scenarios: $SCENARIOS"
echo "  Seeds:     $SEEDS"
echo "  Parallel:  $PARALLEL"
if [[ -n "$AGENT" ]]; then
    echo "  Mode:      Standalone"
    echo "  Agent:     $AGENT"
else
    echo "  Mode:      Remote (A2A)"
    echo "  Agent URL: $AGENT_URL"
fi
echo ""

# Build command
if [[ -n "$AGENT" ]]; then
    CMD="uv run qbench eval --agent $AGENT --scenarios $SCENARIOS --seeds $SEEDS --parallel $PARALLEL $VERBOSE $OUTPUT"
else
    CMD="uv run qbench eval --agent-url $AGENT_URL --scenarios $SCENARIOS --seeds $SEEDS --parallel $PARALLEL $VERBOSE $OUTPUT"
fi

# Run evaluation
echo -e "${GREEN}Starting evaluation...${NC}"
echo ""
echo "Command: $CMD"
echo ""

eval $CMD
EXIT_CODE=$?

echo ""
if [[ $EXIT_CODE -eq 0 ]]; then
    echo -e "${GREEN}✓ Quick test completed successfully!${NC}"
else
    echo -e "${RED}✗ Quick test failed with exit code $EXIT_CODE${NC}"
fi
echo ""

exit $EXIT_CODE
