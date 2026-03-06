"""
Staking CLI commands for ModernTensor

Commands:
- info: Show staking info for an address
- lock: Lock MDT tokens for staking
- unlock: Unlock staked MDT tokens
- stakes: List all stake locks
"""

import click
import os
from typing import Optional
from web3 import Web3

from sdk.cli.ui import (
    print_error,
    print_success,
    print_info,
    print_warning,
    console,
    create_table,
    spinner,
)
from sdk.cli.config import get_network_config


def _get_client(network: str, key: Optional[str] = None):
    """Create a PolkadotClient for the given network."""
    from sdk.polkadot.client import PolkadotClient

    private_key = key or os.environ.get("PRIVATE_KEY")
    if not private_key:
        print_error("No private key. Use --key or set PRIVATE_KEY env var.")
        raise SystemExit(1)
    net_cfg = get_network_config(network)
    return PolkadotClient(
        network=network,
        rpc_url=net_cfg.get("rpc_url"),
        private_key=private_key,
        deployment_path=net_cfg.get("deployment_path"),
    )


@click.group(name="staking", short_help="MDT staking operations")
@click.pass_context
def staking(ctx):
    """
    Staking — Lock MDT tokens for time-weighted bonus rewards.

    Lock durations and bonus rates:
      30+ days  → 10% bonus
      90+ days  → 25% bonus
      180+ days → 50% bonus
      365  days → 100% bonus
    """
    pass


@staking.command("info")
@click.option("--network", default="local", help="Network name")
@click.option("--key", default=None, help="Private key")
@click.option("--address", default=None, help="Address to check (defaults to wallet)")
def staking_info(network: str, key: Optional[str], address: Optional[str]):
    """Show staking info for an address."""
    try:
        client = _get_client(network, key)
        s = client.staking
        target = address or client.address

        with spinner("Fetching staking info..."):
            stake_info = s.get_stake_info(target)

        table = create_table(
            "Staking Info",
            [
                ("Metric", "cyan"),
                ("Value", "green"),
            ],
        )
        table.add_row("Address", target)
        table.add_row("Active Stakes", str(stake_info.active_stakes))
        table.add_row("Total Locked", f"{stake_info.total_locked_ether:.4f} MDT")
        table.add_row("Pending Bonus", f"{stake_info.pending_bonus_ether:.4f} MDT")

        console.print(table)

        # Show total staked in contract
        total = s.total_staked()
        print_info(f"  Total staked in contract: {Web3.from_wei(total, 'ether'):.4f} MDT")

        # Show bonus rates
        print_info("  Bonus rates: 30d→10%, 90d→25%, 180d→50%, 365d→100%")
    except Exception as e:
        print_error(f"Failed to get staking info: {e}")


@staking.command("stakes")
@click.option("--network", default="local", help="Network name")
@click.option("--key", default=None, help="Private key")
@click.option("--address", default=None, help="Address to check")
def staking_stakes(network: str, key: Optional[str], address: Optional[str]):
    """List all stake locks for an address."""
    try:
        client = _get_client(network, key)
        s = client.staking
        target = address or client.address

        with spinner("Fetching stake locks..."):
            stakes = s.get_all_stakes(target)

        if not stakes:
            print_warning("No stake locks found.")
            return

        table = create_table(
            f"Stake Locks ({len(stakes)} total)",
            [
                ("#", "cyan"),
                ("Amount", "green"),
                ("Bonus", "yellow"),
                ("Status", "white"),
            ],
        )
        for i, lock in enumerate(stakes):
            status = (
                "🔓 Unlockable"
                if lock.can_unlock
                else ("✅ Withdrawn" if lock.withdrawn else "🔒 Locked")
            )
            table.add_row(
                str(i),
                f"{lock.amount_ether:.4f} MDT",
                f"{lock.bonus_percent:.1f}%",
                status,
            )
        console.print(table)
    except Exception as e:
        print_error(f"Failed to list stakes: {e}")


@staking.command("lock")
@click.option("--network", default="local", help="Network name")
@click.option("--key", default=None, help="Private key")
@click.argument("amount", type=float)
@click.argument("days", type=int, default=30)
def staking_lock(network: str, key: Optional[str], amount: float, days: int):
    """Lock MDT tokens for staking.

    AMOUNT: MDT tokens to lock (e.g., 100.0)
    DAYS: Lock duration in days (default: 30, max: 365)
    """
    try:
        client = _get_client(network, key)
        s = client.staking

        # Preview bonus rate
        bonus_rate = s.get_bonus_rate(days)
        bonus_pct = bonus_rate / 100.0
        print_info(f"  Lock: {amount} MDT for {days} days → {bonus_pct:.1f}% bonus")

        # Approve + lock in one call
        with spinner(f"Approving and locking {amount} MDT..."):
            approve_tx, lock_tx = s.approve_and_lock(amount, days)

        print_success("Tokens locked!")
        print_info(f"  Amount:    {amount} MDT")
        print_info(f"  Duration:  {days} days")
        print_info(f"  Bonus:     {bonus_pct:.1f}%")
        print_info(f"  Approve TX: {approve_tx}")
        print_info(f"  Lock TX:    {lock_tx}")
    except Exception as e:
        print_error(f"Lock failed: {e}")


@staking.command("unlock")
@click.option("--network", default="local", help="Network name")
@click.option("--key", default=None, help="Private key")
@click.argument("index", type=int)
def staking_unlock(network: str, key: Optional[str], index: int):
    """Unlock staked MDT tokens (after lock period).

    INDEX: Stake lock index (use 'staking stakes' to see available locks)
    """
    try:
        client = _get_client(network, key)
        s = client.staking

        # Check if this lock exists and is unlockable
        lock = s.get_stake_lock(index)
        if lock.withdrawn:
            print_warning(f"Stake #{index} already withdrawn.")
            return
        if not lock.can_unlock:
            print_warning(f"Stake #{index} is still locked.")
            print_info(f"  Unlock time: {lock.unlock_time}")
            return

        with spinner(f"Unlocking stake #{index} ({lock.amount_ether:.4f} MDT)..."):
            tx_hash = s.unlock(index)

        print_success("Tokens unlocked + bonus claimed!")
        print_info(f"  Amount: {lock.amount_ether:.4f} MDT")
        print_info(f"  Bonus:  {lock.bonus_percent:.1f}%")
        print_info(f"  TX:     {tx_hash}")
    except Exception as e:
        print_error(f"Unlock failed: {e}")
