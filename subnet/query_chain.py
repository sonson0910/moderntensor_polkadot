#!/usr/bin/env python3
"""
ModernTensor On-Chain Query — Subnet Demo
═══════════════════════════════════════════

Truy vấn dữ liệu on-chain: subnet info, nodes, weights, metagraph.

Usage:
  python subnet/query_chain.py                # Hiện toàn bộ
  python subnet/query_chain.py subnet         # Chỉ subnet info
  python subnet/query_chain.py nodes          # Chỉ nodes
  python subnet/query_chain.py weights        # Chỉ weights
  python subnet/query_chain.py metagraph      # Chỉ metagraph
"""

import sys
import json
from pathlib import Path
from datetime import datetime

SUBNET_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SUBNET_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

CONFIG_FILE = SUBNET_DIR / "config.json"
with open(CONFIG_FILE) as f:
    CFG = json.load(f)

from web3 import Web3


def connect():
    from sdk.polkadot.client import PolkadotClient
    client = PolkadotClient(
        rpc_url=CFG["network"]["rpc_url"],
        private_key=CFG["wallets"]["deployer"]["key"],
        deployment_path=str(PROJECT_ROOT / CFG["deployment_file"]),
    )
    if not client.is_connected:
        print("  ❌ Cannot connect to Polkadot Hub Testnet")
        sys.exit(1)
    return client


def show_subnet(client, netuid=1):
    """Show subnet configuration."""
    sn = client.subnet.get_subnet(netuid)
    print()
    print("╔" + "═" * 62 + "╗")
    print("║  🌐  SUBNET INFO                                              ║")
    print("╚" + "═" * 62 + "╝")
    print(f"  Name:           {sn.name}")
    print(f"  NetUID:         {netuid}")
    print(f"  Owner:          {sn.owner}")
    print(f"  Max Nodes:      {sn.max_nodes}")
    print(f"  Active Nodes:   {sn.node_count}")
    print(f"  Tempo:          {sn.tempo} block(s)/epoch")
    print(f"  Emission Share: {sn.emission_share} BPS ({sn.emission_share/100:.0f}%)")
    print(f"  Active:         {'✅ Yes' if sn.active else '❌ No'}")
    print(f"  Block:          {client.block_number}")
    print("─" * 64)


def show_nodes(client, netuid=1):
    """Show all nodes in subnet."""
    sn = client.subnet.get_subnet(netuid)
    print()
    print("╔" + "═" * 62 + "╗")
    print("║  👥  SUBNET NODES                                             ║")
    print("╚" + "═" * 62 + "╝")
    print(f"  {'UID':<5} {'Type':<11} {'Hotkey':<15} {'Stake':<12} {'Trust':<10} {'Rank':<10} {'Emission':<12}")
    print(f"  {'─'*5} {'─'*11} {'─'*15} {'─'*12} {'─'*10} {'─'*10} {'─'*12}")

    for uid in range(sn.node_count + 5):
        try:
            node = client.subnet.get_node(netuid, uid)
            if not node.active:
                continue
            ntype = "VALIDATOR" if node.is_validator else "MINER"
            emoji = "🔷" if node.is_validator else "⛏️"
            hotkey_short = node.hotkey[:10] + "..."
            print(
                f"  {emoji}{uid:<4} {ntype:<11} {hotkey_short:<15} "
                f"{node.total_stake_ether:<12.2f} "
                f"{node.trust_float:<10.4f} "
                f"{node.rank_float:<10.6f} "
                f"{node.emission_ether:<12.6f}"
            )
        except Exception:
            continue
    print()


def show_weights(client, netuid=1):
    """Show validator weights."""
    sn = client.subnet.get_subnet(netuid)
    print()
    print("╔" + "═" * 62 + "╗")
    print("║  ⚖️   VALIDATOR WEIGHTS                                       ║")
    print("╚" + "═" * 62 + "╝")

    for uid in range(sn.node_count + 5):
        try:
            node = client.subnet.get_node(netuid, uid)
            if not node.active or not node.is_validator:
                continue
            uids, weights = client.subnet.get_weights(netuid, uid)
            if uids:
                print(f"\n  🔷 Validator UID={uid} (trust={node.trust_float:.4f})")
                for m_uid, w in zip(uids, weights):
                    bar_len = int(w / max(max(weights), 1) * 20)
                    bar = "█" * bar_len + "░" * (20 - bar_len)
                    print(f"     ⛏️ Miner UID={m_uid}: [{bar}] {w}")
        except Exception:
            continue
    print()


def show_metagraph(client, netuid=1):
    """Show full metagraph."""
    meta = client.subnet.get_metagraph(netuid)
    sn = client.subnet.get_subnet(netuid)

    print()
    print(f"╔{'═'*72}╗")
    print(f"║  📊  METAGRAPH: {sn.name:<55}║")
    print(f"╚{'═'*72}╝")
    print(f"  {'UID':<5} {'Type':<11} {'Stake (MDT)':<14} {'Trust':<10} {'Rank':<12} {'Emission (MDT)':<16}")
    print(f"  {'─'*5} {'─'*11} {'─'*14} {'─'*10} {'─'*12} {'─'*16}")

    for node in meta.nodes:
        if not node.active:
            continue
        ntype = "VALIDATOR" if node.is_validator else "MINER"
        emoji = "🔷" if node.is_validator else "⛏️"
        print(
            f"  {emoji}{node.uid:<4} {ntype:<11} "
            f"{node.total_stake_ether:<14.2f} "
            f"{node.trust_float:<10.4f} "
            f"{node.rank_float:<12.6f} "
            f"{node.emission_ether:<16.6f}"
        )

    total = float(Web3.from_wei(meta.total_stake, "ether"))
    print(f"\n  Total Stake: {total:.2f} MDT | Miners: {len(meta.miners)} | Validators: {len(meta.validators)}")
    print(f"  Queried at block {client.block_number} — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()


def main():
    client = connect()
    netuid = CFG["subnet"]["netuid"]

    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if mode in ("all", "subnet"):
        show_subnet(client, netuid)
    if mode in ("all", "nodes"):
        show_nodes(client, netuid)
    if mode in ("all", "weights"):
        show_weights(client, netuid)
    if mode in ("all", "metagraph"):
        show_metagraph(client, netuid)


if __name__ == "__main__":
    main()
