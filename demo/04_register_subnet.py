#!/usr/bin/env python3
"""
ModernTensor Demo — Step 4: Register on Subnet

Registers validator and miner nodes on the subnet with staking.

Usage:
  python demo/04_register_subnet.py
  NETWORK=polkadot_testnet NETUID=1 python demo/04_register_subnet.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from demo.config import (
    get_network,
    HARDHAT_ACCOUNTS,
    VALIDATOR_STAKE,
    MINER_STAKE,
    banner,
    step_log,
    ok,
    info,
    warn,
    fail,
    separator,
)
from web3 import Web3


def register_validator(val_client, netuid, stake_ether):
    """Register a validator on the subnet."""
    step_log("1", "Registering VALIDATOR...")

    subnet = val_client.subnet

    if subnet.is_registered(netuid, val_client.address):
        uid = subnet.get_uid(netuid, val_client.address)
        ok(f"Validator already registered! UID={uid}")
        node = subnet.get_node(netuid, uid)
        info(f"  Stake: {node.total_stake_ether:.2f} MDT | Active: {node.active}")
        return uid

    # Approve stake
    step_log("1a", f"Approving {stake_ether} MDT for validator stake...")
    registry_addr = val_client._get_contract("SubnetRegistry").address
    val_client.token.approve(registry_addr, Web3.to_wei(stake_ether, "ether"))
    ok(f"Approved {stake_ether} MDT")

    # Register
    step_log("1b", "Submitting validator registration TX...")
    tx = subnet.register_validator(
        netuid=netuid,
        hotkey=val_client.address,
        stake_ether=stake_ether,
    )
    ok(f"Registered as VALIDATOR — TX: {tx}")

    uid = subnet.get_uid(netuid, val_client.address)
    node = subnet.get_node(netuid, uid)
    ok(f"  UID: {uid}")
    info(f"  Stake: {node.total_stake_ether:.2f} MDT")
    info(f"  Active: {node.active}")

    return uid


def register_miner(miner_client, netuid, stake_ether):
    """Register a miner on the subnet."""
    step_log("2", "Registering MINER...")

    subnet = miner_client.subnet

    if subnet.is_registered(netuid, miner_client.address):
        uid = subnet.get_uid(netuid, miner_client.address)
        ok(f"Miner already registered! UID={uid}")
        node = subnet.get_node(netuid, uid)
        info(f"  Stake: {node.total_stake_ether:.2f} MDT | Active: {node.active}")
        return uid

    # Approve stake
    step_log("2a", f"Approving {stake_ether} MDT for miner stake...")
    registry_addr = miner_client._get_contract("SubnetRegistry").address
    miner_client.token.approve(registry_addr, Web3.to_wei(stake_ether, "ether"))
    ok(f"Approved {stake_ether} MDT")

    # Register
    step_log("2b", "Submitting miner registration TX...")
    tx = subnet.register_miner(
        netuid=netuid,
        hotkey=miner_client.address,
        stake_ether=stake_ether,
    )
    ok(f"Registered as MINER — TX: {tx}")

    uid = subnet.get_uid(netuid, miner_client.address)
    node = subnet.get_node(netuid, uid)
    ok(f"  UID: {uid}")
    info(f"  Stake: {node.total_stake_ether:.2f} MDT")
    info(f"  Active: {node.active}")

    return uid


def register_miner_as_fulfiller(owner_client, miner_address):
    """Register miner as authorized Oracle fulfiller."""
    step_log("3", "Registering miner as Oracle fulfiller...")
    try:
        tx = owner_client.oracle.register_fulfiller(miner_address)
        ok(f"Miner registered as fulfiller — TX: {tx}")
    except Exception as e:
        info(f"Fulfiller registration: {str(e)[:80]}")


def display_metagraph(client, netuid):
    """Display current subnet metagraph."""
    banner("SUBNET METAGRAPH")

    meta = client.subnet.get_metagraph(netuid)

    print(f"\n  📊 Subnet {netuid}")
    separator()
    print(f"  {'UID':<5} {'Type':<12} {'Hotkey':<16} {'Stake (MDT)':<14} {'Active'}")
    separator()

    for node in meta.nodes:
        node_type = "VALIDATOR" if node.is_validator else "MINER"
        print(
            f"  {node.uid:<5} {node_type:<12} {node.hotkey[:14]}.. "
            f"{node.total_stake_ether:<14.4f} {'Yes' if node.active else 'No'}"
        )

    separator()
    total_stake = Web3.from_wei(meta.total_stake, "ether")
    print(
        f"  Total Stake: {total_stake} MDT | "
        f"Miners: {len(meta.miners)} | Validators: {len(meta.validators)}"
    )


def main():
    print("\n📝 ModernTensor — Register on Subnet")
    print("   Validator + Miner registration with staking\n")

    network_name = os.environ.get("NETWORK", "local")
    netuid = int(os.environ.get("NETUID", "1"))

    from sdk.polkadot.client import PolkadotClient

    net = get_network(network_name)
    info(f"Network: {net['label']}")
    info(f"Target subnet: netuid={netuid}")

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

    # Create clients
    clients = {}
    for role in ["deployer", "validator", "miner"]:
        clients[role] = PolkadotClient(
            rpc_url=net["rpc_url"],
            private_key=wallets[role]["key"],
            deployment_path=net["deployment"],
        )
        ok(f"{role.capitalize()} client: {clients[role].address}")

    # Register validator
    banner("REGISTER VALIDATOR")
    validator_uid = register_validator(clients["validator"], netuid, VALIDATOR_STAKE)

    # Register miner
    banner("REGISTER MINER")
    miner_uid = register_miner(clients["miner"], netuid, MINER_STAKE)

    # Register miner as Oracle fulfiller
    register_miner_as_fulfiller(clients["deployer"], clients["miner"].address)

    # Show metagraph
    display_metagraph(clients["deployer"], netuid)

    banner("REGISTRATION COMPLETE ✅")
    print(
        f"""
  Validator:  UID={validator_uid}, Stake={VALIDATOR_STAKE} MDT
  Miner:      UID={miner_uid}, Stake={MINER_STAKE} MDT
  Fulfiller:  Miner registered as Oracle fulfiller

  Next steps:
    python demo/05_run_miner.py      # Start miner node
    python demo/06_run_validator.py   # Start validator node
    python demo/07_run_demo.py        # Run complete cycle
"""
    )


if __name__ == "__main__":
    main()
