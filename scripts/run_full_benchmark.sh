#!/bin/bash
# QBench Full Benchmark Script
# Runs complete evaluation with all 105 scenarios (35 scenarios × 3 seeds)

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
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
        --parallel)
            PARALLEL="$2"
            shift 2
            ;;
        --fast)
            PARALLEL="50"
            shift
            ;;
        --balanced)
            PARALLEL="10"
            shift
            ;;
        --sequential)
            PARALLEL="1"
            shift
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
            echo "QBench Full Benchmark Script"
            echo ""
            echo "Usage:"
            echo "  Interactive:  ./scripts/run_full_benchmark.sh"
            echo "  Standalone:   ./scripts/run_full_benchmark.sh --agent <module.class>"
            echo "  Remote:       ./scripts/run_full_benchmark.sh --agent-url <url>"
            echo ""
            echo "Options:"
            echo "  --parallel N       Parallel workers (default: 1)"
            echo "  --fast             Quick preset: parallel=50 (~1 min)"
            echo "  --balanced         Balanced preset: parallel=10 (~4 min)"
            echo "  --sequential       Sequential preset: parallel=1 (~40 min)"
            echo "  --verbose          Show detailed logs"
            echo "  --output FILE      Output file path"
            echo ""
            echo "Examples:"
            echo "  ./scripts/run_full_benchmark.sh --agent examples.standalone.agent.GPT52Agent --balanced"
            echo "  ./scripts/run_full_benchmark.sh --agent-url http://localhost:9019 --fast"
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
echo "QBench Full Benchmark (105 Episodes)"
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

    # Ask about performance preset
    echo ""
    echo "Choose performance mode:"
    echo "  1) Sequential  (parallel=1,  ~35-45 min, easier debugging)"
    echo "  2) Balanced    (parallel=10, ~4-5 min,  recommended)"
    echo "  3) Fast        (parallel=50, ~1-2 min,  requires good hardware)"
    echo ""
    read -p "Selection [1-3] (default: 2): " perf_selection

    case $perf_selection in
        1)
            PARALLEL="1"
            ;;
        3)
            PARALLEL="50"
            ;;
        2|"")
            PARALLEL="10"
            ;;
        *)
            echo -e "${YELLOW}Invalid selection, using balanced (parallel=10)${NC}"
            PARALLEL="10"
            ;;
    esac
fi

# Estimate time based on parallel workers
if [[ $PARALLEL -le 1 ]]; then
    TIME_ESTIMATE="35-45 minutes"
elif [[ $PARALLEL -le 10 ]]; then
    TIME_ESTIMATE="4-5 minutes"
else
    TIME_ESTIMATE="1-2 minutes"
fi

# Show configuration and warning
echo ""
echo "=============================================="
echo "Configuration:"
echo "  Scenarios:   35 types × 3 seeds = 105 episodes"
echo "  Parallel:    $PARALLEL workers"
echo "  Estimated:   $TIME_ESTIMATE"
if [[ -n "$AGENT" ]]; then
    echo "  Mode:        Standalone"
    echo "  Agent:       $AGENT"
else
    echo "  Mode:        Remote (A2A)"
    echo "  Agent URL:   $AGENT_URL"
fi
echo "=============================================="
echo ""
echo -e "${YELLOW}⚠️  WARNING: This will run the complete benchmark${NC}"
echo -e "${YELLOW}⚠️  If using an LLM agent, estimated cost: ~\$3-4${NC}"
echo ""

# Confirmation
read -p "Continue with full benchmark? [y/N]: " confirm
if [[ ! $confirm =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Create results directory
mkdir -p results

# Generate timestamp for output if not specified
if [[ -z "$OUTPUT" ]]; then
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    OUTPUT="--output results/full_benchmark_${TIMESTAMP}.json"
fi

# Build command
if [[ -n "$AGENT" ]]; then
    CMD="uv run qbench eval --agent $AGENT --parallel $PARALLEL $VERBOSE $OUTPUT"
else
    CMD="uv run qbench eval --agent-url $AGENT_URL --parallel $PARALLEL $VERBOSE $OUTPUT"
fi

# Run evaluation
echo ""
echo -e "${GREEN}Starting full benchmark...${NC}"
echo "⏱️  Start time: $(date)"
echo ""
echo "Command: $CMD"
echo ""

START_TIME=$(date +%s)
eval $CMD
EXIT_CODE=$?
END_TIME=$(date +%s)

# Calculate duration
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

echo ""
echo "=============================================="
if [[ $EXIT_CODE -eq 0 ]]; then
    echo -e "${GREEN}✓ Full benchmark completed successfully!${NC}"
else
    echo -e "${RED}✗ Benchmark failed with exit code $EXIT_CODE${NC}"
fi
echo "=============================================="
echo ""
echo "⏱️  Total time: ${MINUTES}m ${SECONDS}s"
if [[ $OUTPUT =~ --output\ (.+) ]]; then
    OUTPUT_FILE="${BASH_REMATCH[1]}"
    echo "📊 Results saved to: $OUTPUT_FILE"
fi
echo ""

exit $EXIT_CODE
