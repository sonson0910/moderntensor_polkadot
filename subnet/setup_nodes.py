#!/usr/bin/env python3
"""
ModernTensor — Fresh Subnet Setup (2 Miners + 3 Validators)
═══════════════════════════════════════════════════════════════

Generates 2 new coldkeys, funds them, registers 5 nodes.
Self-vote protection: 1 coldkey for miners, 1 coldkey for validators.

Usage:
  python subnet/setup_nodes.py
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

SUBNET_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SUBNET_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from eth_account import Account
from web3 import Web3
from rich.table import Table

from sdk.cli.ui import (
    console, print_banner, print_error, print_divider,
    print_status_box, print_success, print_info,
)

CONFIG_FILE = SUBNET_DIR / "config.json"
with open(CONFIG_FILE) as f:
    CFG = json.load(f)

RPC_URL = CFG["network"]["rpc_url"]
NETUID = CFG["subnet"]["netuid"]
DEPLOYMENT = str(PROJECT_ROOT / CFG["deployment_file"])
CHAIN_ID = CFG["network"]["chain_id"]

STAKE_PER_NODE = 100  # MDT
GAS_PER_KEY = 5       # PAS

def log(emoji, msg, **kw):
    ts = datetime.now().strftime("%H:%M:%S")
    extra = " | ".join(f"{k}={v}" for k, v in kw.items()) if kw else ""
    suffix = f"  [dim]({extra})[/dim]" if extra else ""
    console.print(f"  [dim][{ts}][/dim] {emoji} {msg}{suffix}")


def send_pas(deployer_client, to_addr, amount_ether, deployer_key):
    """Send PAS native tokens."""
    w3 = deployer_client.w3
    deployer_addr = deployer_client.address
    nonce = w3.eth.get_transaction_count(deployer_addr)
    tx = {
        "from": deployer_addr,
        "to": Web3.to_checksum_address(to_addr),
        "value": Web3.to_wei(amount_ether, "ether"),
        "gas": 21000,
        "gasPrice": w3.eth.gas_price,
        "nonce": nonce,
        "chainId": CHAIN_ID,
    }
    signed = w3.eth.account.sign_transaction(tx, deployer_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    return tx_hash.hex()


def main():
    from sdk.polkadot.client import PolkadotClient

    print_banner(
        title="ModernTensor — Fresh Subnet Setup",
        subtitle="2 Miners + 3 Validators on Polkadot Hub Testnet",
        icon="🛠️",
    )

    # ── Connect deployer ─────────────────────────────────────
    deployer_key = CFG["wallets"]["deployer"]["key"]
    deployer = PolkadotClient(
        rpc_url=RPC_URL, private_key=deployer_key, deployment_path=DEPLOYMENT,
    )
    if not deployer.is_connected:
        print_error("Cannot connect"); sys.exit(1)
    log("🌐", f"Connected", block=deployer.block_number)

    deployer_addr = deployer.address
    pas_bal = deployer.w3.eth.get_balance(deployer_addr)
    mdt_bal = deployer.token.balance_of(deployer_addr)
    log("💰", f"Deployer PAS: {Web3.from_wei(pas_bal, 'ether'):.4f}")
    log("💰", f"Deployer MDT: {Web3.from_wei(mdt_bal, 'ether'):.2f}")

    # ═══════════════════════════════════════════════════════════
    # Step 1: Generate 2 coldkeys + 5 hotkeys
    # ═══════════════════════════════════════════════════════════
    print_divider("Step 1/5: Generate Keys")

    miner_coldkey = Account.create()
    validator_coldkey = Account.create()
    log("🔑", f"Miner coldkey:     {miner_coldkey.address}")
    log("🔑", f"Validator coldkey:  {validator_coldkey.address}")

    # Generate 5 separate hotkeys (network identity)
    hotkeys = []
    for i in range(5):
        hk = Account.create()
        role = f"miner{i+1}" if i < 2 else f"validator{i-1}"
        hotkeys.append({"name": role, "address": hk.address, "key": hk.key.hex()})
        log("🔑", f"Hotkey {role}: {hk.address}")

    # ═══════════════════════════════════════════════════════════
    # Step 2: Fund coldkeys with PAS (native gas)
    # ═══════════════════════════════════════════════════════════
    print_divider("Step 2/5: Fund PAS (Gas)")
    for name, addr in [("miner_coldkey", miner_coldkey.address),
                        ("validator_coldkey", validator_coldkey.address)]:
        log("💸", f"Sending {GAS_PER_KEY} PAS to {name}")
        try:
            tx = send_pas(deployer, addr, GAS_PER_KEY, deployer_key)
            log("✅", f"Funded {name}", tx=tx[:16] + "...")
        except Exception as e:
            print_error(f"PAS funding failed: {e}"); sys.exit(1)
        time.sleep(2)

    # ═══════════════════════════════════════════════════════════
    # Step 3: Fund coldkeys with MDT (staking tokens)
    # ═══════════════════════════════════════════════════════════
    print_divider("Step 3/5: Fund MDT (Stake)")
    # Miner coldkey needs 200 MDT (2 miners × 100), validator needs 300 MDT (3 × 100)
    for name, addr, amount in [("miner_coldkey", miner_coldkey.address, 200),
                                ("validator_coldkey", validator_coldkey.address, 300)]:
        log("💸", f"Sending {amount} MDT to {name}")
        try:
            tx = deployer.token.transfer(addr, Web3.to_wei(amount, "ether"))
            log("✅", f"Funded {amount} MDT", tx=tx[:16] + "...")
        except Exception as e:
            print_error(f"MDT funding failed: {e}"); sys.exit(1)
        time.sleep(2)

    # ═══════════════════════════════════════════════════════════
    # Step 4: Register nodes
    # ═══════════════════════════════════════════════════════════
    print_divider("Step 4/5: Register Nodes")

    registered = {}

    # Register 2 miners (same miner coldkey, different hotkeys)
    miner_client = PolkadotClient(
        rpc_url=RPC_URL, private_key=miner_coldkey.key.hex(), deployment_path=DEPLOYMENT,
    )
    for i in range(2):
        hk = hotkeys[i]
        log("📝", f"Registering {hk['name']} as MINER (hotkey={hk['address'][:16]}...)")
        try:
            approve_tx, reg_tx = miner_client.subnet.approve_and_register_miner(
                NETUID, stake_ether=STAKE_PER_NODE, hotkey=hk["address"]
            )
            # Get UID via contract mapping
            uid = miner_client.subnet._contract.functions.hotkeyToUid(NETUID, Web3.to_checksum_address(hk["address"])).call()
            registered[hk["name"]] = {"uid": uid, "hotkey": hk["address"], "type": "MINER"}
            log("🎉", f"{hk['name']} → MINER UID={uid}", tx=reg_tx[:16] + "...")
        except Exception as e:
            log("❌", f"Register failed: {e}")
        time.sleep(2)

    # Register 3 validators (same validator coldkey, different hotkeys)
    val_client = PolkadotClient(
        rpc_url=RPC_URL, private_key=validator_coldkey.key.hex(), deployment_path=DEPLOYMENT,
    )
    for i in range(2, 5):
        hk = hotkeys[i]
        log("📝", f"Registering {hk['name']} as VALIDATOR (hotkey={hk['address'][:16]}...)")
        try:
            approve_tx, reg_tx = val_client.subnet.approve_and_register_validator(
                NETUID, stake_ether=STAKE_PER_NODE, hotkey=hk["address"]
            )
            uid = val_client.subnet._contract.functions.hotkeyToUid(NETUID, Web3.to_checksum_address(hk["address"])).call()
            registered[hk["name"]] = {"uid": uid, "hotkey": hk["address"], "type": "VALIDATOR"}
            log("🎉", f"{hk['name']} → VALIDATOR UID={uid}", tx=reg_tx[:16] + "...")
        except Exception as e:
            log("❌", f"Register failed: {e}")
        time.sleep(2)

    # ═══════════════════════════════════════════════════════════
    # Step 5: Fund emission pool & save config
    # ═══════════════════════════════════════════════════════════
    print_divider("Step 5/5: Finalize")

    # Fund emission pool
    try:
        deployer.token.approve(deployer.subnet._contract.address, Web3.to_wei(50000, "ether"))
        time.sleep(2)
        pool_tx = deployer.subnet.fund_emission_pool(50000)
        log("💰", "Funded emission pool +50,000 MDT", tx=pool_tx[:16] + "...")
    except Exception as e:
        log("ℹ️", f"Emission pool: {str(e)[:60]}")

    # Save new config
    new_config = {
        "network": CFG["network"],
        "subnet": CFG["subnet"],
        "deployment_file": CFG["deployment_file"],
        "wallets": {
            "deployer": CFG["wallets"]["deployer"],
            "miner_coldkey": {
                "key": miner_coldkey.key.hex(),
                "address": miner_coldkey.address,
            },
            "validator_coldkey": {
                "key": validator_coldkey.key.hex(),
                "address": validator_coldkey.address,
            },
        },
        "nodes": {},
        "timing": CFG["timing"],
    }
    for name, info in registered.items():
        new_config["nodes"][name] = {"hotkey": info["hotkey"], "uid": info["uid"]}

    config_path = SUBNET_DIR / "config.json"
    with open(config_path, "w") as f:
        json.dump(new_config, f, indent=4)
    log("💾", "Config updated → config.json")

    # ── Print summary table ────────────────────────────────────
    print_divider("Setup Complete ✅")

    table = Table(
        show_header=True,
        header_style="bold brand",
        border_style="dim",
    )
    table.add_column("Name", width=12)
    table.add_column("Type", width=11)
    table.add_column("UID", justify="right", width=6)
    table.add_column("Hotkey", width=44)

    for name, info in registered.items():
        emoji = "⛏️" if info["type"] == "MINER" else "🔷"
        table.add_row(
            f"{emoji}{name}",
            info["type"],
            str(info["uid"]),
            info["hotkey"],
        )

    console.print(table)

    print_info(f"Miner coldkey:     {miner_coldkey.address}")
    print_info(f"Validator coldkey: {validator_coldkey.address}")
    print_success("💡 Next step: python subnet/run_full_demo.py")
    console.print()


if __name__ == "__main__":
    main()
