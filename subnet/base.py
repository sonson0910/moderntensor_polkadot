"""
ModernTensor Subnet — Shared Base Module
═════════════════════════════════════════

Common code for all miners and validators.
"""

import os
import sys
import json
import time
import hashlib
import random
import signal
import uuid
from pathlib import Path
from datetime import datetime

from web3 import Web3

# ═══════════════════════════════════════════════════════════
# Paths & Config
# ═══════════════════════════════════════════════════════════
SUBNET_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SUBNET_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

CONFIG_FILE = SUBNET_DIR / "config.json"
TASK_DIR = SUBNET_DIR / "task_queue"
TASK_DIR.mkdir(exist_ok=True)

with open(CONFIG_FILE) as f:
    CFG = json.load(f)

RPC_URL      = CFG["network"]["rpc_url"]
CHAIN_ID     = CFG["network"]["chain_id"]
NETUID       = CFG["subnet"]["netuid"]
DEPLOYMENT   = str(PROJECT_ROOT / CFG["deployment_file"])


def get_client(wallet_key_name: str):
    """Create a PolkadotClient from a wallet key name in config."""
    from sdk.polkadot.client import PolkadotClient
    key = CFG["wallets"][wallet_key_name]["key"]
    client = PolkadotClient(
        rpc_url=RPC_URL,
        private_key=key,
        deployment_path=DEPLOYMENT,
    )
    return client


def get_deployer():
    """Get deployer client (for setWeights / runEpoch as owner)."""
    return get_client("deployer")


def log(emoji, msg, **kw):
    """Pretty log with timestamp."""
    ts = datetime.now().strftime("%H:%M:%S")
    extra = " | ".join(f"{k}={v}" for k, v in kw.items()) if kw else ""
    print(f"  [{ts}] {emoji} {msg}" + (f"  ({extra})" if extra else ""))


def show_metagraph(client, netuid=None):
    """Display the full subnet metagraph table."""
    netuid = netuid or NETUID
    try:
        meta = client.subnet.get_metagraph(netuid)
        sn = client.subnet.get_subnet(netuid)

        print(f"\n  ╭── Metagraph: {sn.name} (netuid={netuid}) @ block {client.block_number} ───╮")
        print(f"  │ {'UID':<5} {'Type':<11} {'Stake':<12} {'Trust':<10} {'Rank':<12} {'Emission':<14} │")
        print(f"  │ {'─'*5} {'─'*11} {'─'*12} {'─'*10} {'─'*12} {'─'*14} │")

        for node in meta.nodes:
            if not node.active:
                continue
            ntype = "VALIDATOR" if node.is_validator else "MINER"
            emoji_n = "🔷" if node.is_validator else "⛏️"
            print(
                f"  │ {emoji_n}{node.uid:<4} {ntype:<11} "
                f"{node.total_stake_ether:<12.2f} "
                f"{node.trust_float:<10.4f} "
                f"{node.rank_float:<12.6f} "
                f"{node.emission_ether:<14.6f} │"
            )

        total = float(Web3.from_wei(meta.total_stake, "ether"))
        print(f"  │{'─'*74}│")
        print(f"  │ Total Stake: {total:.2f} MDT | Miners: {len(meta.miners)} | Validators: {len(meta.validators)}")
        print(f"  ╰{'─'*74}╯\n")
    except Exception as e:
        log("⚠️", f"Metagraph error: {str(e)[:60]}")


# ═══════════════════════════════════════════════════════════
# AI Models (shared by miners)
# ═══════════════════════════════════════════════════════════
AI_MODELS = {
    "NLP": {
        "name": "ModernBERT-Sentiment-v3",
        "params": "355M",
        "run": lambda text: {
            "output": f"Sentiment: {'POSITIVE' if random.random() > 0.3 else 'NEGATIVE'} ({random.uniform(0.75, 0.98):.2f})",
            "confidence": random.uniform(0.80, 0.99),
            "details": {
                "key_phrases": random.sample(["blockchain", "decentralized", "AI", "inference", "trust", "network", "Polkadot"], 3),
                "emotional_tone": random.choice(["Optimistic", "Neutral", "Analytical"]),
                "domain_tags": ["technology", "web3", "AI"],
            },
        },
    },
    "Finance": {
        "name": "FinanceGPT-Risk-v2",
        "params": "1.2B",
        "run": lambda text: {
            "output": f"Risk: {random.choice(['LOW', 'MEDIUM', 'HIGH'])} — Score {random.uniform(2, 9):.1f}/10",
            "confidence": random.uniform(0.78, 0.96),
            "details": {
                "risk_factors": random.sample(["volatility", "liquidity", "smart_contract", "impermanent_loss", "leverage"], 3),
                "recommendation": random.choice(["Hold", "Reduce exposure", "Hedge with options"]),
                "var_95": f"${random.uniform(1000, 15000):.0f}",
            },
        },
    },
    "Code": {
        "name": "CodeAuditLLM-v4",
        "params": "780M",
        "run": lambda text: {
            "output": f"Severity: {random.choice(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'])} — {random.choice(['reentrancy', 'overflow', 'access control', 'underflow'])}",
            "confidence": random.uniform(0.80, 0.97),
            "details": {
                "vulnerability": random.choice(["missing require", "unchecked return", "delegatecall risk"]),
                "fix": "Use SafeMath / OpenZeppelin guards",
                "lines_affected": random.randint(1, 5),
            },
        },
    },
}


def generate_zkml_proof(model_name, input_data, output_data):
    """Generate simulated zkML proof."""
    payload = f"{model_name}:{input_data}:{output_data}:{time.time()}"
    proof_hash = hashlib.sha256(payload.encode()).hexdigest()
    return proof_hash


# ═══════════════════════════════════════════════════════════
# Task Catalog (shared by validators)
# ═══════════════════════════════════════════════════════════
TASK_CATALOG = [
    {
        "domain": "NLP",
        "domain_name": "Natural Language Processing",
        "task_name": "Sentiment Analysis",
        "inputs": [
            "Polkadot's parachain architecture enables unprecedented interoperability between blockchains.",
            "ModernTensor brings decentralized AI inference to the Polkadot ecosystem through zkML proofs.",
            "Web3 AI solutions are transforming how we approach data privacy and model ownership.",
            "The convergence of blockchain and AI creates new paradigms for trustless computation.",
            "Decentralized GPU networks will democratize AI access for developers worldwide.",
        ],
    },
    {
        "domain": "Finance",
        "domain_name": "Financial Analysis",
        "task_name": "Risk Assessment",
        "inputs": [
            "Portfolio: ETH 40%, DOT 30%, MDT 20%, USDC 10% — 1.5x leverage, 90 days.",
            "DeFi lending: $50k AAVE at 5.2% APY, health factor 1.8. Evaluate safety.",
            "Cross-chain LP: 3 positions across parachains, TVL $120k. CalculateIL risk.",
        ],
    },
    {
        "domain": "Code",
        "domain_name": "Smart Contract Security",
        "task_name": "Smart Contract Audit",
        "inputs": [
            "function transfer(address to, uint256 amount) external { balances[msg.sender] -= amount; balances[to] += amount; }",
            "function withdraw() external { (bool ok,) = msg.sender.call{value: balances[msg.sender]}(''); balances[msg.sender] = 0; }",
            "function approve(address spender, uint256 amount) public { allowance[msg.sender][spender] = amount; }",
        ],
    },
]
