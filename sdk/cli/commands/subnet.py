"""
Subnet management commands for ModernTensor CLI

Commands:
- create: Create a new subnet
- list: List all subnets
- info: Show subnet details
- register: Register as miner/validator on subnet
- deregister: Deregister from subnet
- set-weights: Set weights on miners (validators only)
- metagraph: Display subnet metagraph
- delegate: Delegate stake to validator
- undelegate: Undelegate stake from validator
- claim: Claim accumulated emission rewards
- run-epoch: Trigger epoch emission distribution
"""

import click
from typing import Optional

from sdk.cli.ui import (
    print_error, print_success, print_info, print_warning,
    confirm_action, console, create_table, print_panel, spinner
)
from sdk.cli.config import get_network_config


def _get_client(network: str, private_key: Optional[str] = None):
    """Create PolkadotClient from network config."""
    import os
    from sdk.polkadot.client import PolkadotClient

    config = get_network_config(network)
    key = private_key or os.environ.get("PRIVATE_KEY")
    return PolkadotClient(
        rpc_url=config.rpc_url,
        private_key=key,
    )


@click.group(name='subnet', short_help='Manage subnets and neurons')
@click.pass_context
def subnet(ctx):
    """
    Subnet management commands

    Create and manage subnets, register as miner/validator,
    set weights, view metagraph, delegate stake, and claim rewards.
    """
    pass


# ═══════════════════════════════════════════════════════
# Subnet CRUD
# ═══════════════════════════════════════════════════════

@subnet.command('create')
@click.option('--name', required=True, help='Subnet name (max 64 chars)')
@click.option('--max-nodes', default=256, help='Maximum neurons allowed')
@click.option('--min-stake', default=0.0, type=float, help='Minimum stake in MDT')
@click.option('--tempo', default=360, type=int, help='Blocks per epoch')
@click.option('--network', default='polkadot_testnet', help='Network name')
@click.option('--private-key', envvar='PRIVATE_KEY', help='Private key for signing')
@click.pass_context
def create_subnet(ctx, name, max_nodes, min_stake, tempo, network, private_key):
    """
    Create a new subnet (burns registration cost)

    Example:
        mtcli subnet create --name "AI Compute" --max-nodes 256 --tempo 360
    """
    try:
        client = _get_client(network, private_key)
        print_info(f"Creating subnet '{name}' on {network}...")
        print_info(f"  Max nodes: {max_nodes}, Min stake: {min_stake} MDT, Tempo: {tempo}")

        with spinner("Sending transaction..."):
            tx_hash = client.subnet.create_subnet(
                name=name,
                max_nodes=max_nodes,
                min_stake_ether=min_stake,
                tempo=tempo,
            )

        print_success(f"Subnet created! TX: {tx_hash}")
        count = client.subnet.get_subnet_count()
        print_info(f"Total subnets: {count}")

    except Exception as e:
        print_error(f"Failed to create subnet: {e}")


@subnet.command('list')
@click.option('--network', default='polkadot_testnet', help='Network name')
@click.option('--private-key', envvar='PRIVATE_KEY', help='Private key')
@click.pass_context
def list_subnets(ctx, network, private_key):
    """
    List all subnets

    Example:
        mtcli subnet list --network polkadot_testnet
    """
    try:
        client = _get_client(network, private_key)
        count = client.subnet.get_subnet_count()

        if count == 0:
            print_warning("No subnets found")
            return

        table = create_table("Subnets", ["NetUID", "Name", "Owner", "Nodes", "Emission%", "Tempo", "Active"])
        for i in range(1, count + 1):
            try:
                info = client.subnet.get_subnet(i)
                table.add_row(
                    str(info.netuid),
                    info.name,
                    info.owner[:10] + "...",
                    str(info.node_count),
                    f"{info.emission_percent:.1f}%",
                    str(info.tempo),
                    "Yes" if info.active else "No",
                )
            except Exception:
                pass

        console.print(table)
        print_info(f"Total subnets: {count}")

    except Exception as e:
        print_error(f"Failed to list subnets: {e}")


@subnet.command('info')
@click.argument('netuid', type=int)
@click.option('--network', default='polkadot_testnet', help='Network name')
@click.option('--private-key', envvar='PRIVATE_KEY', help='Private key')
@click.pass_context
def subnet_info(ctx, netuid, network, private_key):
    """
    Show detailed subnet info

    Example:
        mtcli subnet info 1
    """
    try:
        client = _get_client(network, private_key)
        info = client.subnet.get_subnet(netuid)

        text = f"""[bold cyan]NetUID:[/bold cyan] {info.netuid}
[bold cyan]Name:[/bold cyan] {info.name}
[bold cyan]Owner:[/bold cyan] {info.owner}
[bold cyan]Max Nodes:[/bold cyan] {info.max_nodes}
[bold cyan]Node Count:[/bold cyan] {info.node_count}
[bold cyan]Emission Share:[/bold cyan] {info.emission_percent:.1f}%
[bold cyan]Tempo:[/bold cyan] {info.tempo} blocks
[bold cyan]Active:[/bold cyan] {"Yes" if info.active else "No"}"""

        print_panel(text, title=f"Subnet {netuid}", border_style="cyan")

    except Exception as e:
        print_error(f"Failed to get subnet info: {e}")


# ═══════════════════════════════════════════════════════
# Node Registration
# ═══════════════════════════════════════════════════════

@subnet.command('register')
@click.argument('netuid', type=int)
@click.option('--role', required=True, type=click.Choice(['miner', 'validator']), help='Node role')
@click.option('--stake', default=0.0, type=float, help='Initial stake in MDT')
@click.option('--hotkey', default=None, help='Hotkey address (defaults to caller)')
@click.option('--network', default='polkadot_testnet', help='Network name')
@click.option('--private-key', envvar='PRIVATE_KEY', help='Private key')
@click.option('--yes', is_flag=True, help='Skip confirmation')
@click.pass_context
def register(ctx, netuid, role, stake, hotkey, network, private_key, yes):
    """
    Register as miner or validator on a subnet

    Examples:
        mtcli subnet register 1 --role miner --stake 50
        mtcli subnet register 1 --role validator --stake 100
    """
    try:
        client = _get_client(network, private_key)

        print_info(f"Registering as {role} on subnet {netuid}")
        if stake > 0:
            print_info(f"Initial stake: {stake} MDT")

        if not yes and not confirm_action(f"Register as {role} on subnet {netuid}?"):
            return

        with spinner("Registering..."):
            if role == "miner":
                if stake > 0:
                    _, tx_hash = client.subnet.approve_and_register_miner(netuid, stake, hotkey)
                else:
                    tx_hash = client.subnet.register_miner(netuid, hotkey, stake)
            else:
                if stake > 0:
                    _, tx_hash = client.subnet.approve_and_register_validator(netuid, stake, hotkey)
                else:
                    tx_hash = client.subnet.register_validator(netuid, hotkey, stake)

        print_success(f"Registered as {role}! TX: {tx_hash}")
        uid = client.subnet.get_uid(netuid, hotkey)
        print_info(f"Assigned UID: {uid}")

    except Exception as e:
        print_error(f"Failed to register: {e}")


@subnet.command('deregister')
@click.argument('netuid', type=int)
@click.argument('uid', type=int)
@click.option('--network', default='polkadot_testnet', help='Network name')
@click.option('--private-key', envvar='PRIVATE_KEY', help='Private key')
@click.option('--yes', is_flag=True, help='Skip confirmation')
@click.pass_context
def deregister(ctx, netuid, uid, network, private_key, yes):
    """
    Deregister a node from subnet

    Example:
        mtcli subnet deregister 1 0
    """
    try:
        client = _get_client(network, private_key)
        if not yes and not confirm_action(f"Deregister UID {uid} from subnet {netuid}?"):
            return

        with spinner("Deregistering..."):
            tx_hash = client.subnet.deregister(netuid, uid)

        print_success(f"Deregistered! TX: {tx_hash}")

    except Exception as e:
        print_error(f"Failed to deregister: {e}")


# ═══════════════════════════════════════════════════════
# Weight Setting
# ═══════════════════════════════════════════════════════

@subnet.command('set-weights')
@click.argument('netuid', type=int)
@click.option('--uids', required=True, help='Comma-separated miner UIDs')
@click.option('--weights', required=True, help='Comma-separated weights (0-65535)')
@click.option('--network', default='polkadot_testnet', help='Network name')
@click.option('--private-key', envvar='PRIVATE_KEY', help='Private key')
@click.pass_context
def set_weights(ctx, netuid, uids, weights, network, private_key):
    """
    Set weights on miners (validators only)

    Example:
        mtcli subnet set-weights 1 --uids "0,1,2" --weights "100,200,50"
    """
    try:
        client = _get_client(network, private_key)

        uid_list = [int(u.strip()) for u in uids.split(",")]
        weight_list = [int(w.strip()) for w in weights.split(",")]

        if len(uid_list) != len(weight_list):
            print_error("UIDs and weights must have the same length")
            return

        print_info(f"Setting weights on subnet {netuid}")
        for u, w in zip(uid_list, weight_list):
            print_info(f"  UID {u} → weight {w}")

        with spinner("Setting weights..."):
            tx_hash = client.subnet.set_weights(netuid, uid_list, weight_list)

        print_success(f"Weights set! TX: {tx_hash}")

    except Exception as e:
        print_error(f"Failed to set weights: {e}")


# ═══════════════════════════════════════════════════════
# Metagraph
# ═══════════════════════════════════════════════════════

@subnet.command('metagraph')
@click.argument('netuid', type=int)
@click.option('--network', default='polkadot_testnet', help='Network name')
@click.option('--private-key', envvar='PRIVATE_KEY', help='Private key')
@click.pass_context
def metagraph(ctx, netuid, network, private_key):
    """
    Display subnet metagraph

    Shows all registered nodes with their stakes, ranks, and emission.

    Example:
        mtcli subnet metagraph 1
    """
    try:
        client = _get_client(network, private_key)

        with spinner("Fetching metagraph..."):
            meta = client.subnet.get_metagraph(netuid)

        if not meta.nodes:
            print_warning(f"No nodes in subnet {netuid}")
            return

        table = create_table(
            f"Metagraph — Subnet {netuid}",
            ["UID", "Type", "Hotkey", "Stake (MDT)", "Rank", "Emission (MDT)", "Active"]
        )

        for node in meta.nodes:
            table.add_row(
                str(node.uid),
                "Validator" if node.is_validator else "Miner",
                node.hotkey[:10] + "...",
                f"{node.total_stake_ether:.4f}",
                f"{node.rank_float:.6f}",
                f"{node.emission_ether:.6f}",
                "Yes" if node.active else "No",
            )

        console.print(table)
        print_info(f"Miners: {len(meta.miners)}  Validators: {len(meta.validators)}")
        from web3 import Web3
        total_stake = Web3.from_wei(meta.total_stake, "ether")
        print_info(f"Total Stake: {total_stake:.4f} MDT")

    except Exception as e:
        print_error(f"Failed to get metagraph: {e}")


# ═══════════════════════════════════════════════════════
# Delegation
# ═══════════════════════════════════════════════════════

@subnet.command('delegate')
@click.argument('netuid', type=int)
@click.argument('validator_uid', type=int)
@click.option('--amount', required=True, type=float, help='Amount in MDT')
@click.option('--network', default='polkadot_testnet', help='Network name')
@click.option('--private-key', envvar='PRIVATE_KEY', help='Private key')
@click.option('--yes', is_flag=True, help='Skip confirmation')
@click.pass_context
def delegate_stake(ctx, netuid, validator_uid, amount, network, private_key, yes):
    """
    Delegate stake to a validator

    Example:
        mtcli subnet delegate 1 0 --amount 100
    """
    try:
        client = _get_client(network, private_key)
        if not yes and not confirm_action(f"Delegate {amount} MDT to validator UID {validator_uid}?"):
            return

        with spinner("Delegating..."):
            _, tx_hash = client.subnet.approve_and_delegate(netuid, validator_uid, amount)

        print_success(f"Delegated {amount} MDT! TX: {tx_hash}")

    except Exception as e:
        print_error(f"Failed to delegate: {e}")


@subnet.command('undelegate')
@click.argument('netuid', type=int)
@click.argument('validator_uid', type=int)
@click.option('--amount', required=True, type=float, help='Amount in MDT')
@click.option('--network', default='polkadot_testnet', help='Network name')
@click.option('--private-key', envvar='PRIVATE_KEY', help='Private key')
@click.option('--yes', is_flag=True, help='Skip confirmation')
@click.pass_context
def undelegate_stake(ctx, netuid, validator_uid, amount, network, private_key, yes):
    """
    Undelegate stake from a validator

    Example:
        mtcli subnet undelegate 1 0 --amount 50
    """
    try:
        client = _get_client(network, private_key)
        if not yes and not confirm_action(f"Undelegate {amount} MDT from validator UID {validator_uid}?"):
            return

        with spinner("Undelegating..."):
            tx_hash = client.subnet.undelegate(netuid, validator_uid, amount)

        print_success(f"Undelegated {amount} MDT! TX: {tx_hash}")

    except Exception as e:
        print_error(f"Failed to undelegate: {e}")


# ═══════════════════════════════════════════════════════
# Emission
# ═══════════════════════════════════════════════════════

@subnet.command('claim')
@click.argument('netuid', type=int)
@click.argument('uid', type=int)
@click.option('--network', default='polkadot_testnet', help='Network name')
@click.option('--private-key', envvar='PRIVATE_KEY', help='Private key')
@click.pass_context
def claim_emission(ctx, netuid, uid, network, private_key):
    """
    Claim accumulated emission rewards

    Example:
        mtcli subnet claim 1 0
    """
    try:
        client = _get_client(network, private_key)

        # Check pending emission
        node = client.subnet.get_node(netuid, uid)
        print_info(f"Pending emission: {node.emission_ether:.6f} MDT")

        if node.emission == 0:
            print_warning("No emission to claim")
            return

        with spinner("Claiming emission..."):
            tx_hash = client.subnet.claim_emission(netuid, uid)

        print_success(f"Claimed! TX: {tx_hash}")

    except Exception as e:
        print_error(f"Failed to claim: {e}")


@subnet.command('run-epoch')
@click.argument('netuid', type=int)
@click.option('--network', default='polkadot_testnet', help='Network name')
@click.option('--private-key', envvar='PRIVATE_KEY', help='Private key')
@click.pass_context
def run_epoch(ctx, netuid, network, private_key):
    """
    Trigger epoch emission distribution (anyone can call when ready)

    Example:
        mtcli subnet run-epoch 1
    """
    try:
        client = _get_client(network, private_key)
        print_info(f"Running epoch for subnet {netuid}...")

        with spinner("Processing epoch..."):
            tx_hash = client.subnet.run_epoch(netuid)

        print_success(f"Epoch complete! TX: {tx_hash}")

    except Exception as e:
        print_error(f"Failed to run epoch: {e}")
