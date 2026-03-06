#!/usr/bin/env python3
"""
ModernTensor Demo — Step 3: Faucet & Token Distribution

On local Hardhat: Distribute MDT tokens from deployer to validator/miner.
On testnet: Request faucet tokens + distribute MDT.

Usage:
  python demo/03_faucet.py
  NETWORK=polkadot_testnet python demo/03_faucet.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from demo.config import (
    get_network,
    get_private_key,
    HARDHAT_ACCOUNTS,
    TOKEN_TO_VALIDATOR,
    TOKEN_TO_MINER,
    banner,
    step_log,
    ok,
    info,
    warn,
    fail,
    separator,
)
from web3 import Web3


def distribute_mdt_tokens(network_name="local"):
    """Distribute MDT from deployer to validator and miner."""
    banner("FAUCET — Token Distribution")

    from sdk.polkadot.client import PolkadotClient

    net = get_network(network_name)
    info(f"Network: {net['label']}")

    # Load wallets
    if network_name == "local":
        wallets = HARDHAT_ACCOUNTS
    else:
        import json

        wallet_file = Path(__file__).resolve().parent / "wallets.json"
        if not wallet_file.exists():
            fail("No wallets found. Run: python demo/02_register_keys.py")
        with open(wallet_file) as f:
            wallets = json.load(f)

    # Create deployer client
    deployer = PolkadotClient(
        rpc_url=net["rpc_url"],
        private_key=wallets["deployer"]["key"],
        deployment_path=net["deployment"],
    )

    ok(f"Connected as deployer: {deployer.address}")

    # Check deployer MDT balance
    step_log("1", "Checking deployer MDT balance...")
    token = deployer.token
    deployer_balance = token.balance_of_ether(deployer.address)
    ok(f"Deployer MDT: {deployer_balance:,.2f}")

    if deployer_balance < (TOKEN_TO_VALIDATOR + TOKEN_TO_MINER):
        warn("Low MDT balance — attempting TGE mint...")
        try:
            tx = token.execute_tge(0, deployer.address)
            ok(f"TGE mint TX: {tx}")
            deployer_balance = token.balance_of_ether(deployer.address)
            ok(f"New balance: {deployer_balance:,.2f} MDT")
        except Exception as e:
            info(f"TGE note: {str(e)[:100]}")

    # Distribute tokens
    distributions = [
        ("validator", TOKEN_TO_VALIDATOR),
        ("miner", TOKEN_TO_MINER),
    ]

    for role, amount in distributions:
        addr = wallets[role]["address"]
        step_log(f"2.{role[0]}", f"Distributing {amount:,} MDT → {role} ({addr[:14]}...)")

        current = token.balance_of_ether(addr)
        if current >= amount:
            ok(f"Already has {current:,.2f} MDT (≥ {amount})")
            continue

        tx = token.transfer(addr, Web3.to_wei(amount, "ether"))
        ok(f"Sent {amount:,} MDT — TX: {tx}")

        new_balance = token.balance_of_ether(addr)
        info(f"  {role.capitalize()} balance: {new_balance:,.2f} MDT")

    # Summary
    banner("TOKEN BALANCES")
    print(f"\n  {'Role':>10} | {'MDT Balance':>18} | {'ETH Balance':>14}")
    separator()

    w3 = Web3(Web3.HTTPProvider(net["rpc_url"]))
    for role, w in wallets.items():
        mdt = token.balance_of_ether(w["address"])
        eth = Web3.from_wei(w3.eth.get_balance(w["address"]), "ether")
        print(f"  {'✅':>2} {role:>8} | {mdt:>18,.2f} | {eth:>14.4f}")


def request_testnet_faucet(network_name):
    """Show instructions for getting testnet tokens."""
    banner("TESTNET FAUCET")

    net = get_network(network_name)

    print(
        f"""
  Network: {net['label']}

  To get testnet tokens:
  ───────────────────────
  1. Polkadot Hub Testnet:
     • Visit: https://faucet.polkadot.io/
     • Select network: Polkadot Hub Testnet
     • Enter your deployer address
     • Wait for confirmation

  2. Westend:
     • Visit: https://faucet.polkadot.io/westend
     • Get WND tokens for gas

  After receiving testnet ETH, run this script again
  to distribute MDT tokens.
"""
    )


def main():
    print("\n💰 ModernTensor — Faucet & Token Distribution")
    print("   Get tokens for demo operations\n")

    network_name = os.environ.get("NETWORK", "local")

    if network_name != "local":
        request_testnet_faucet(network_name)

    distribute_mdt_tokens(network_name)

    banner("FAUCET COMPLETE ✅")
    print(
        f"""
  Tokens distributed:
    Validator: {TOKEN_TO_VALIDATOR:,} MDT (for staking & delegation)
    Miner:     {TOKEN_TO_MINER:,} MDT (for staking & registration)

  Next: python demo/04_register_subnet.py
"""
    )


if __name__ == "__main__":
    main()
