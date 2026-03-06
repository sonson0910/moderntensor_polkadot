#!/usr/bin/env python3
"""
ModernTensor Demo — Step 2: Register Keys (Wallet Setup)

Creates or loads wallets for deployer, validator, and miner roles.
On local Hardhat, uses default accounts. On testnet, generates new keys.

Usage:
  python demo/02_register_keys.py
  NETWORK=polkadot_testnet python demo/02_register_keys.py
"""

import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from demo.config import (
    get_network,
    HARDHAT_ACCOUNTS,
    PROJECT_ROOT,
    banner,
    step_log,
    ok,
    info,
    warn,
    fail,
    separator,
)
from web3 import Web3
from eth_account import Account


WALLET_FILE = PROJECT_ROOT / "demo" / "wallets.json"


def generate_wallet():
    """Generate a new Ethereum wallet."""
    acct = Account.create()
    return {
        "address": acct.address,
        "key": acct.key.hex(),
    }


def load_or_create_wallets(network_name="local"):
    """Load existing wallets or create new ones."""
    banner("REGISTER KEYS — Wallet Setup")

    net = get_network(network_name)
    info(f"Network: {net['label']}")

    if network_name == "local":
        step_log("1", "Using Hardhat default accounts (pre-funded with 10,000 ETH)")
        wallets = {}
        for role, acct in HARDHAT_ACCOUNTS.items():
            wallets[role] = acct
            ok(f"{role.capitalize():>10}: {acct['address']}")
        info("No key generation needed — Hardhat provides funded accounts")
        return wallets

    # Testnet: load or generate
    step_log("1", "Checking for existing wallets...")

    if WALLET_FILE.exists():
        with open(WALLET_FILE) as f:
            wallets = json.load(f)
        ok(f"Loaded {len(wallets)} wallets from {WALLET_FILE.name}")
        for role, w in wallets.items():
            ok(f"{role.capitalize():>10}: {w['address']}")
        return wallets

    step_log("2", "Generating new wallets...")
    wallets = {}
    for role in ["deployer", "validator", "miner"]:
        w = generate_wallet()
        wallets[role] = w
        ok(f"{role.capitalize():>10}: {w['address']}")

    # Save wallets (keys are sensitive — demo only!)
    with open(WALLET_FILE, "w") as f:
        json.dump(wallets, f, indent=2)
    ok(f"Wallets saved to {WALLET_FILE}")
    warn("⚠️  wallets.json contains PRIVATE KEYS — for demo/testnet only!")

    return wallets


def check_balances(wallets, network_name="local"):
    """Check ETH and MDT balances for all wallets."""
    banner("BALANCE CHECK")

    net = get_network(network_name)
    w3 = Web3(Web3.HTTPProvider(net["rpc_url"]))

    if not w3.is_connected():
        fail(f"Cannot connect to {net['rpc_url']}")

    print(f"\n  {'Role':>10} | {'Address':>44} | {'ETH Balance':>14}")
    separator()

    for role, w in wallets.items():
        balance = w3.eth.get_balance(w["address"])
        eth = Web3.from_wei(balance, "ether")
        status = "✅" if balance > 0 else "⚠️ "
        print(f"  {status} {role:>8} | {w['address']} | {eth:>14.4f}")

    # Check MDT balance if contracts are deployed
    try:
        from sdk.polkadot.client import PolkadotClient

        deployer_key = wallets.get("deployer", {}).get("key", "")
        if deployer_key:
            client = PolkadotClient(
                rpc_url=net["rpc_url"],
                private_key=deployer_key,
                deployment_path=net["deployment"],
            )
            print(f"\n  {'Role':>10} | {'MDT Balance':>18}")
            separator()
            for role, w in wallets.items():
                mdt = client.token.balance_of_ether(w["address"])
                status = "✅" if mdt > 0 else "⚠️ "
                print(f"  {status} {role:>8} | {mdt:>18,.2f} MDT")
    except Exception:
        info("Contracts not yet deployed — MDT balances unavailable")

    return wallets


def main():
    print("\n🔑 ModernTensor — Register Keys")
    print("   Wallet creation & balance check\n")

    network_name = os.environ.get("NETWORK", "local")

    wallets = load_or_create_wallets(network_name)
    check_balances(wallets, network_name)

    banner("KEY REGISTRATION COMPLETE ✅")
    print(
        f"""
  Wallets ready for:
    Deployer/Owner .. Contract deployment & administration
    Validator ....... Subnet validation, weight setting, AI tasks
    Miner ........... AI inference, proof generation, rewards

  Next: python demo/03_faucet.py
"""
    )


if __name__ == "__main__":
    main()
