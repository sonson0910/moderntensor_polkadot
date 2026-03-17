#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
# ModernTensor — Full Demo Runner
# Polkadot Hub Testnet
#
# Orchestrates the complete demo flow:
#   Step 1: Deploy 8 smart contracts
#   Step 2: Register hotkeys (deployer / validator / miner)
#   Step 3: Faucet — distribute MDT tokens + add stake
#   Step 4: Register validator & miner on subnet
#   Step 5: Miner inference + zkML proof (1 round)
#   Step 6: Validator task + weight setting + epoch (1 round)
#
# Optional:
#   --live       After setup, launch miner & validator as long-running
#                background processes (Ctrl+C to stop both)
#   --skip-deploy   Skip steps 1–3 if contracts are already deployed
#   --help       Show usage
#
# Usage:
#   bash demo/run_demo.sh              # Full demo (one-shot)
#   bash demo/run_demo.sh --live       # Full demo then long-running mode
#   bash demo/run_demo.sh --skip-deploy # Skip deploy, run steps 4–6 only
# ═══════════════════════════════════════════════════════════════════════════
set -euo pipefail

# ── Paths ────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Colors ───────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'  # No Color

# ── Flags ────────────────────────────────────────────────────────────────
LIVE_MODE=false
SKIP_DEPLOY=false
MINER_PID=""
VALIDATOR_PID=""

# ── Parse arguments ──────────────────────────────────────────────────────
for arg in "$@"; do
  case "$arg" in
    --live)       LIVE_MODE=true ;;
    --skip-deploy) SKIP_DEPLOY=true ;;
    --help|-h)
      echo ""
      echo "  ModernTensor Demo Runner — Polkadot Hub Testnet"
      echo ""
      echo "  Usage:  bash demo/run_demo.sh [OPTIONS]"
      echo ""
      echo "  Options:"
      echo "    --live          After one-shot demo, launch miner & validator"
      echo "                    as long-running background processes"
      echo "    --skip-deploy   Skip steps 1–3 (contracts already deployed)"
      echo "    --help, -h      Show this help message"
      echo ""
      echo "  Environment:"
      echo "    NETUID          Subnet ID (default: 1)"
      echo "    MAX_ROUNDS      Max rounds for steps 5/6 (default: 1)"
      echo "    POLL_INTERVAL   Seconds between validator rounds (default: 10)"
      echo ""
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $arg${NC}"
      echo "Run with --help for usage."
      exit 1
      ;;
  esac
done

# ── Cleanup trap ─────────────────────────────────────────────────────────
cleanup() {
  echo ""
  echo -e "${YELLOW}  ⏹️  Shutting down...${NC}"
  if [[ -n "$MINER_PID" ]] && kill -0 "$MINER_PID" 2>/dev/null; then
    echo "  Stopping miner (PID $MINER_PID)..."
    kill "$MINER_PID" 2>/dev/null || true
    wait "$MINER_PID" 2>/dev/null || true
  fi
  if [[ -n "$VALIDATOR_PID" ]] && kill -0 "$VALIDATOR_PID" 2>/dev/null; then
    echo "  Stopping validator (PID $VALIDATOR_PID)..."
    kill "$VALIDATOR_PID" 2>/dev/null || true
    wait "$VALIDATOR_PID" 2>/dev/null || true
  fi
  # Clean up task queue
  rm -f "$SCRIPT_DIR/task_queue/task_"*.json 2>/dev/null || true
  echo -e "${GREEN}  👋 Demo stopped.${NC}"
  echo ""
}
trap cleanup EXIT INT TERM

# ── Helpers ──────────────────────────────────────────────────────────────
banner() {
  echo ""
  echo -e "${BOLD}╔══════════════════════════════════════════════════════════╗${NC}"
  echo -e "${BOLD}║  🚀  ModernTensor — Full Demo Runner                    ║${NC}"
  echo -e "${BOLD}║  Polkadot Hub Testnet                                   ║${NC}"
  echo -e "${BOLD}╚══════════════════════════════════════════════════════════╝${NC}"
  echo ""
}

step_header() {
  local step_num="$1"
  local total="$2"
  local title="$3"
  echo ""
  echo -e "${CYAN}  ═══════════════════════════════════════════════════════${NC}"
  echo -e "${CYAN}  [STEP ${step_num}/${total}]  ${BOLD}${title}${NC}"
  echo -e "${CYAN}  ═══════════════════════════════════════════════════════${NC}"
  echo ""
}

run_script() {
  local script="$1"
  shift
  local script_path="$SCRIPT_DIR/$script"

  if [[ ! -f "$script_path" ]]; then
    echo -e "${RED}  ❌ Script not found: $script_path${NC}"
    exit 1
  fi

  echo -e "${GREEN}  ▶ Running: python $script_path $*${NC}"
  echo ""
  python3 "$script_path" "$@"
  local exit_code=$?

  if [[ $exit_code -ne 0 ]]; then
    echo ""
    echo -e "${RED}  ❌ Script failed: $script (exit code $exit_code)${NC}"
    exit $exit_code
  fi

  echo ""
  echo -e "${GREEN}  ✅ $script completed successfully${NC}"
}

# ── Prerequisites ────────────────────────────────────────────────────────
check_prerequisites() {
  echo "  Checking prerequisites..."

  if ! command -v python3 &>/dev/null; then
    echo -e "${RED}  ❌ python3 not found. Install Python 3.8+.${NC}"
    exit 1
  fi
  echo -e "  ✓ python3 $(python3 --version 2>&1 | awk '{print $2}')"

  if ! python3 -c "import web3" 2>/dev/null; then
    echo -e "${RED}  ❌ web3 Python module not found.${NC}"
    echo "     Install: pip install web3"
    exit 1
  fi
  echo "  ✓ web3 module"

  if [[ ! -f "$SCRIPT_DIR/config.py" ]]; then
    echo -e "${RED}  ❌ demo/config.py not found${NC}"
    exit 1
  fi
  echo "  ✓ demo/config.py"

  echo -e "${GREEN}  All prerequisites met.${NC}"
}

# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════
main() {
  banner
  check_prerequisites

  local total_steps=6

  # ── Steps 1–3: Deploy & Setup ──────────────────────────────────────
  if [[ "$SKIP_DEPLOY" == true ]]; then
    local results_file="$PROJECT_ROOT/luxtensor/contracts/demo-results.json"
    if [[ ! -f "$results_file" ]]; then
      echo -e "${RED}  ❌ --skip-deploy requires demo-results.json to exist${NC}"
      echo "     Run without --skip-deploy first."
      exit 1
    fi
    echo -e "${YELLOW}  ⏭️  Skipping steps 1–3 (--skip-deploy)${NC}"
  else
    step_header 1 $total_steps "Deploy Smart Contracts"
    run_script "01_deploy_setup.py"

    step_header 2 $total_steps "Register Hotkeys"
    run_script "02_register_keys.py"

    step_header 3 $total_steps "Faucet — Distribute MDT Tokens"
    run_script "03_faucet.py"
  fi

  # ── Step 4: Register on Subnet ─────────────────────────────────────
  step_header 4 $total_steps "Register Validator & Miner on Subnet"
  run_script "04_register_subnet.py"

  # ── Step 5: Miner Inference ────────────────────────────────────────
  step_header 5 $total_steps "Miner Inference + zkML Proofs"
  MAX_ROUNDS="${MAX_ROUNDS:-1}" run_script "05_run_miner.py"

  # ── Step 6: Validator Consensus ────────────────────────────────────
  step_header 6 $total_steps "Validator Consensus + Epoch"
  MAX_ROUNDS="${MAX_ROUNDS:-1}" run_script "06_run_validator.py"

  # ── Summary ────────────────────────────────────────────────────────
  echo ""
  echo -e "${BOLD}╔══════════════════════════════════════════════════════════╗${NC}"
  echo -e "${BOLD}║  ✅  Demo Complete!                                      ║${NC}"
  echo -e "${BOLD}╚══════════════════════════════════════════════════════════╝${NC}"
  echo ""

  # ── Live mode ──────────────────────────────────────────────────────
  if [[ "$LIVE_MODE" == true ]]; then
    echo ""
    echo -e "${CYAN}  ═══════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  [LIVE MODE]  ${BOLD}Launching Miner & Validator${NC}"
    echo -e "${CYAN}  ═══════════════════════════════════════════════════════${NC}"
    echo ""

    # Clean up old tasks
    rm -f "$SCRIPT_DIR/task_queue/task_"*.json 2>/dev/null || true

    # Launch miner in background
    echo -e "${GREEN}  ▶ Starting miner...${NC}"
    python3 "$SCRIPT_DIR/miner.py" &
    MINER_PID=$!
    echo "    PID: $MINER_PID"

    sleep 3

    # Launch validator in background
    echo -e "${GREEN}  ▶ Starting validator...${NC}"
    python3 "$SCRIPT_DIR/validator.py" &
    VALIDATOR_PID=$!
    echo "    PID: $VALIDATOR_PID"

    echo ""
    echo -e "${YELLOW}  Press Ctrl+C to stop both processes${NC}"
    echo ""

    # Wait for both processes
    wait "$MINER_PID" "$VALIDATOR_PID" 2>/dev/null || true
  fi
}

main
