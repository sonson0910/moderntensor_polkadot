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
from sdk.cli.ui import (
    console, print_banner, print_error, print_divider,
    print_status_box, print_metagraph_table,
)


def connect():
    from sdk.polkadot.client import PolkadotClient
    client = PolkadotClient(
        rpc_url=CFG["network"]["rpc_url"],
        private_key=CFG["wallets"]["deployer"]["key"],
        deployment_path=str(PROJECT_ROOT / CFG["deployment_file"]),
    )
    if not client.is_connected:
        print_error("Cannot connect to Polkadot Hub Testnet")
        sys.exit(1)
    return client


def show_subnet(client, netuid=1):
    """Show subnet configuration."""
    sn = client.subnet.get_subnet(netuid)
    print_banner(
        title="SUBNET INFO",
        subtitle=sn.name,
        details={
            "NetUID":         str(netuid),
            "Owner":          sn.owner,
            "Max Nodes":      str(sn.max_nodes),
            "Active Nodes":   str(sn.node_count),
            "Tempo":          f"{sn.tempo} block(s)/epoch",
            "Emission Share": f"{sn.emission_share} BPS ({sn.emission_share/100:.0f}%)",
            "Active":         "✅ Yes" if sn.active else "❌ No",
            "Block":          str(client.block_number),
        },
        icon="🌐",
    )


def show_nodes(client, netuid=1):
    """Show all nodes in subnet."""
    from rich.table import Table

    sn = client.subnet.get_subnet(netuid)

    print_divider("SUBNET NODES 👥")

    table = Table(
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
        title_style="cyan",
    )
    table.add_column("UID", justify="right", width=5)
    table.add_column("Type", width=11)
    table.add_column("Hotkey", width=15)
    table.add_column("Stake", justify="right", width=12)
    table.add_column("Trust", justify="right", width=10)
    table.add_column("Rank", justify="right", width=10)
    table.add_column("Emission", justify="right", width=12)

    for uid in range(sn.node_count + 5):
        try:
            node = client.subnet.get_node(netuid, uid)
            if not node.active:
                continue
            ntype = "VALIDATOR" if node.is_validator else "MINER"
            emoji = "🔷" if node.is_validator else "⛏️"
            hotkey_short = node.hotkey[:10] + "..."
            table.add_row(
                f"{emoji}{uid}",
                ntype,
                hotkey_short,
                f"{node.total_stake_ether:.2f}",
                f"{node.trust_float:.4f}",
                f"{node.rank_float:.6f}",
                f"{node.emission_ether:.6f}",
            )
        except Exception:
            continue

    console.print(table)
    console.print()


def show_weights(client, netuid=1):
    """Show validator weights."""
    sn = client.subnet.get_subnet(netuid)

    print_divider("VALIDATOR WEIGHTS ⚖️")

    for uid in range(sn.node_count + 5):
        try:
            node = client.subnet.get_node(netuid, uid)
            if not node.active or not node.is_validator:
                continue
            uids, weights = client.subnet.get_weights(netuid, uid)
            if uids:
                console.print(
                    f"\n  [bold cyan]🔷 Validator UID={uid}[/] "
                    f"(trust={node.trust_float:.4f})"
                )
                for m_uid, w in zip(uids, weights):
                    bar_len = int(w / max(max(weights), 1) * 20)
                    bar = "█" * bar_len + "░" * (20 - bar_len)
                    console.print(
                        f"     [dim]⛏️ Miner UID={m_uid}:[/] "
                        f"[cyan][{bar}][/cyan] {w}"
                    )
        except Exception:
            continue
    console.print()


def show_metagraph_full(client, netuid=1):
    """Show full metagraph via Rich helper."""
    sn = client.subnet.get_subnet(netuid)
    nodes = []
    for uid in range(sn.node_count + 5):
        try:
            node = client.subnet.get_node(netuid, uid)
            if node.active:
                nodes.append(node)
        except Exception:
            continue
    n_validators = sum(1 for n in nodes if n.is_validator)
    n_miners = len(nodes) - n_validators
    total_stake = sum(n.total_stake_ether for n in nodes)
    print_metagraph_table(
        nodes=nodes,
        total_stake=f"{total_stake:.4f}",
        n_miners=n_miners,
        n_validators=n_validators,
        title="Metagraph",
        block=client.block_number,
    )



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
        show_metagraph_full(client, netuid)


if __name__ == "__main__":
    main()
