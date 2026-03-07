"""
AI Orchestrator CLI commands for ModernTensor

ModernTensor supports ANY AI domain — NLP, Vision, Finance, Health,
Code Review, and more. Each domain runs as a subnet with its own
model, scoring, and zkML verification pipeline.

Commands:
- status: Show AI subnet metagraph
- create-task: Create an AI inference task (any domain)
- evaluate: Show current miner weights
"""

import click
import os
from typing import Optional

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


@click.group(name="ai", short_help="AI inference & evaluation")
@click.pass_context
def ai(ctx):
    """
    AI — Multi-domain inference, evaluation, and orchestration.

    ModernTensor supports ANY AI vertical as a subnet:
    - NLP (text analysis, sentiment, translation)
    - Vision (image classification, object detection)
    - Finance (risk scoring, fraud detection)
    - Health (medical data analysis, diagnostics)
    - Code Review (security audit, quality scoring)
    - And more...

    The core loop: validators create tasks → miners process with
    zkML proofs → weights set based on verified AI performance.
    """
    pass


@ai.command("status")
@click.option("--network", default="local", help="Network name")
@click.option("--key", default=None, help="Private key")
@click.option("--netuid", default=1, type=int, help="Subnet UID")
def ai_status(network: str, key: Optional[str], netuid: int):
    """Show AI subnet status and metagraph."""
    try:
        client = _get_client(network, key)

        with spinner("Fetching subnet metagraph..."):
            mg = client.subnet.get_metagraph(netuid)

        table = create_table(
            f"Subnet {netuid} — Metagraph",
            [
                ("UID", "cyan"),
                ("Role", "blue"),
                ("Stake", "green"),
                ("Rank", "yellow"),
                ("Emission", "magenta"),
                ("Active", "white"),
            ],
        )

        for node in mg.nodes:
            role = "🔍 Validator" if node.node_type == 1 else "⛏️ Miner"
            table.add_row(
                str(node.uid),
                role,
                f"{node.stake_ether:.4f}",
                f"{node.rank:.4f}" if node.rank else "0.0",
                f"{node.emission_ether:.6f}",
                "✅" if node.is_active else "❌",
            )

        console.print(table)
        print_info(f"  Total nodes: {len(mg.nodes)}")
    except Exception as e:
        print_error(f"Failed to get AI status: {e}")


@ai.command("create-task")
@click.option("--network", default="local", help="Network name")
@click.option("--key", default=None, help="Private key")
@click.option("--netuid", default=1, type=int, help="Subnet UID")
@click.option(
    "--model",
    required=True,
    help="Model name (e.g. 'nlp-sentiment-v1', 'vision-classify-v1', 'code-review-v1')",
)
@click.option("--input", "input_data", required=True, help="Input data for inference")
@click.option("--payment", default=0.01, type=float, help="Payment in MDT")
def ai_create_task(
    network: str, key: Optional[str], netuid: int, model: str, input_data: str, payment: float
):
    """Create an AI inference task on-chain (any domain).

    Examples:
      mtcli ai create-task --model nlp-sentiment-v1 --input "Analyze this text"
      mtcli ai create-task --model vision-classify-v1 --input "classify:cat.jpg"
      mtcli ai create-task --model finance-risk-v1 --input "score:portfolio_data"
      mtcli ai create-task --model code-review-v1 --input "Review: function foo(){}"
    """
    try:
        client = _get_client(network, key)
        orch = client.orchestrator(netuid=netuid)

        input_bytes = input_data.encode("utf-8")

        with spinner(f"Creating {model} task..."):
            task = orch.create_inference_task(
                model_name=model,
                input_data=input_bytes,
                payment_ether=payment,
            )

        print_success("Task created!")
        print_info(f"  Model:    {task.model_name}")
        print_info(f"  Task ID:  {task.task_id}")
        print_info(f"  Payment:  {payment} MDT")
        print_info(f"  Oracle TX: {task.oracle_tx}")
    except Exception as e:
        print_error(f"Task creation failed: {e}")


@ai.command("evaluate")
@click.option("--network", default="local", help="Network name")
@click.option("--key", default=None, help="Private key (validator)")
@click.option("--netuid", default=1, type=int, help="Subnet UID")
def ai_evaluate(network: str, key: Optional[str], netuid: int):
    """Show current miner weights set by validators."""
    try:
        client = _get_client(network, key)

        # Get metagraph to show current weights
        with spinner("Fetching current weights..."):
            mg = client.subnet.get_metagraph(netuid)

        validators = [n for n in mg.nodes if n.node_type == 1 and n.is_active]
        miners = [n for n in mg.nodes if n.node_type == 0 and n.is_active]

        print_info(f"  Active validators: {len(validators)}")
        print_info(f"  Active miners:     {len(miners)}")

        for val in validators:
            uids, weights = client.subnet.get_weights(netuid, val.uid)
            if uids:
                table = create_table(
                    f"Weights by Validator UID={val.uid}",
                    [
                        ("Miner UID", "cyan"),
                        ("Weight", "green"),
                    ],
                )
                for u, w in zip(uids, weights):
                    table.add_row(str(u), str(w))
                console.print(table)
            else:
                print_warning(f"  Validator UID={val.uid}: No weights set yet")
    except Exception as e:
        print_error(f"Evaluation failed: {e}")
