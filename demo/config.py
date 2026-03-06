"""
ModernTensor Demo — Shared Configuration

All demo scripts share these constants and utilities.
Supports: local Hardhat node + Polkadot Hub Testnet
"""

import os
import sys
import json
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ═══════════════════════════════════════════════════════════
# Network Configuration
# ═══════════════════════════════════════════════════════════
NETWORKS = {
    "local": {
        "rpc_url": "http://127.0.0.1:8545",
        "chain_id": 31337,
        "deployment": str(PROJECT_ROOT / "luxtensor" / "contracts" / "deployments-polkadot.json"),
        "label": "Local Hardhat Node",
    },
    "polkadot_testnet": {
        "rpc_url": "https://services.polkadothub-rpc.com/testnet",
        "chain_id": 420420417,
        "deployment": str(PROJECT_ROOT / "luxtensor" / "contracts" / "deployments-polkadot.json"),
        "label": "Polkadot Hub Testnet",
    },
    "westend": {
        "rpc_url": "https://westend-asset-hub-eth-rpc.polkadot.io",
        "chain_id": 420420421,
        "deployment": str(PROJECT_ROOT / "luxtensor" / "contracts" / "deployments-polkadot.json"),
        "label": "Westend Asset Hub",
    },
}

# ═══════════════════════════════════════════════════════════
# Default Hardhat Accounts (for local demo)
# ═══════════════════════════════════════════════════════════
HARDHAT_ACCOUNTS = {
    "deployer": {
        "key": "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
        "address": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
    },
    "validator": {
        "key": "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",
        "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
    },
    "miner": {
        "key": "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a",
        "address": "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC",
    },
}

# ═══════════════════════════════════════════════════════════
# Subnet Defaults
# ═══════════════════════════════════════════════════════════
SUBNET_NAME = "ModernTensor AI Subnet"
SUBNET_MAX_NODES = 256
SUBNET_MIN_STAKE = 10  # MDT
SUBNET_TEMPO = 10  # blocks (small for demo, 360 in production)
VALIDATOR_STAKE = 100  # MDT to stake for validator
MINER_STAKE = 50  # MDT to stake for miner
TOKEN_TO_VALIDATOR = 5000  # MDT to distribute
TOKEN_TO_MINER = 1000  # MDT to distribute
EMISSION_FUND = 10000  # MDT for emission pool

# AI Model names (trusted in zkML & approved in Oracle)
AI_MODELS = [
    "moderntensor-nlp-sentiment-v1",
    "moderntensor-finance-risk-v1",
    "moderntensor-code-review-v1",
]


# ═══════════════════════════════════════════════════════════
# Utility Helpers
# ═══════════════════════════════════════════════════════════
def get_network(name=None):
    """Get network config. Priority: arg > env > default (local)."""
    network = name or os.environ.get("NETWORK", "local")
    if network not in NETWORKS:
        print(f"❌ Unknown network: {network}")
        print(f"   Available: {', '.join(NETWORKS.keys())}")
        sys.exit(1)
    return NETWORKS[network]


def get_private_key(role="deployer"):
    """Get private key. Priority: env > hardhat default."""
    env_key = os.environ.get("PRIVATE_KEY")
    if env_key:
        return env_key
    if role in HARDHAT_ACCOUNTS:
        return HARDHAT_ACCOUNTS[role]["key"]
    return HARDHAT_ACCOUNTS["deployer"]["key"]


def banner(title, width=60):
    print(f"\n{'═' * width}")
    print(f"  🔷 {title}")
    print(f"{'═' * width}")


def step_log(num, text):
    print(f"\n  [{num}] {text}")


def ok(text):
    print(f"      ✅ {text}")


def info(text):
    print(f"      ℹ️  {text}")


def warn(text):
    print(f"      ⚠️  {text}")


def fail(text):
    print(f"      ❌ {text}")
    sys.exit(1)


def separator():
    print(f"  {'─' * 50}")
