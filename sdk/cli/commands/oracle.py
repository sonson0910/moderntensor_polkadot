"""
AI Oracle CLI commands for ModernTensor

Commands:
- request: Submit AI inference request
- fulfill: Fulfill a pending AI request (miner)
- status: Check request status by ID
- approve-model: Approve a model hash (admin)
- info: Show oracle statistics
"""

import click
import os
from typing import Optional
from web3 import Web3

from sdk.cli.ui import print_error, print_success, print_info, console, create_table, spinner
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


@click.group(name="oracle", short_help="AI Oracle operations")
@click.pass_context
def oracle(ctx):
    """
    AI Oracle — Decentralized AI inference on-chain.

    Submit AI requests, fulfill them as a miner, and manage models.
    """
    pass


@oracle.command("info")
@click.option("--network", default="local", help="Network name")
@click.option("--key", default=None, help="Private key")
def oracle_info(network: str, key: Optional[str]):
    """Show AI Oracle statistics."""
    try:
        client = _get_client(network, key)
        o = client.oracle

        table = create_table(
            "AI Oracle Status",
            [
                ("Metric", "cyan"),
                ("Value", "green"),
            ],
        )
        table.add_row("Total Requests", str(o.total_requests()))
        table.add_row("Protocol Fee", f"{o.protocol_fee_bps()} bps")
        table.add_row("Contract", str(client._addresses.get("AIOracle", "N/A")))

        console.print(table)
    except Exception as e:
        print_error(f"Failed to get oracle info: {e}")


@oracle.command("request")
@click.option("--network", default="local", help="Network name")
@click.option("--key", default=None, help="Private key")
@click.option("--model", required=True, help="Model name (e.g. moderntensor-code-review-v1)")
@click.option("--input", "input_data", required=True, help="Input data string")
@click.option("--payment", default=0.01, type=float, help="Payment in native token (ETH)")
@click.option("--timeout", default=0, type=int, help="Timeout in blocks (0=default)")
def oracle_request(
    network: str, key: Optional[str], model: str, input_data: str, payment: float, timeout: int
):
    """Submit an AI inference request with payment."""
    try:
        client = _get_client(network, key)
        model_hash = Web3.keccak(text=model)

        with spinner("Submitting AI request..."):
            tx_hash = client.oracle.request_ai(
                model_hash=model_hash,
                input_data=input_data.encode("utf-8"),
                timeout=timeout,
                payment_ether=payment,
            )

        print_success(f"AI request submitted!")
        print_info(f"  TX Hash:    {tx_hash}")
        print_info(f"  Model:      {model}")
        print_info(f"  Model Hash: {model_hash.hex()[:20]}...")
        print_info(f"  Payment:    {payment} ETH")
    except Exception as e:
        print_error(f"Request failed: {e}")


@oracle.command("fulfill")
@click.option("--network", default="local", help="Network name")
@click.option("--key", default=None, help="Private key")
@click.option("--request-id", required=True, help="Request ID (32-byte hex)")
@click.option("--result", "result_data", required=True, help="AI output data")
@click.option("--proof", default=None, help="zkML proof hash (optional)")
def oracle_fulfill(
    network: str, key: Optional[str], request_id: str, result_data: str, proof: Optional[str]
):
    """Fulfill a pending AI request (miner operation)."""
    try:
        client = _get_client(network, key)

        req_id_bytes = bytes.fromhex(request_id.removeprefix("0x"))
        proof_bytes = bytes.fromhex(proof.removeprefix("0x")) if proof else b"\x00" * 32

        with spinner("Fulfilling AI request..."):
            tx_hash = client.oracle.fulfill_request(
                request_id=req_id_bytes,
                result=result_data.encode("utf-8"),
                proof_hash=proof_bytes,
            )

        print_success(f"Request fulfilled!")
        print_info(f"  TX Hash: {tx_hash}")
    except Exception as e:
        print_error(f"Fulfill failed: {e}")


@oracle.command("status")
@click.option("--network", default="local", help="Network name")
@click.option("--key", default=None, help="Private key")
@click.argument("request_id")
def oracle_status(network: str, key: Optional[str], request_id: str):
    """Check status of an AI request by ID."""
    try:
        client = _get_client(network, key)

        req_id_bytes = bytes.fromhex(request_id.removeprefix("0x"))
        req = client.oracle.get_request(req_id_bytes)

        status_map = {0: "⏳ PENDING", 1: "✅ FULFILLED", 2: "❌ CANCELLED", 3: "⏰ EXPIRED"}

        table = create_table(
            "AI Request Details",
            [
                ("Field", "cyan"),
                ("Value", "green"),
            ],
        )
        table.add_row("Request ID", request_id[:20] + "...")
        table.add_row("Requester", req.requester)
        table.add_row("Status", status_map.get(req.status, str(req.status)))
        table.add_row("Reward", f"{req.reward_ether:.6f} ETH")
        table.add_row("Created At", f"Block {req.created_at}")
        table.add_row("Deadline", f"Block {req.deadline}")
        if req.is_fulfilled:
            table.add_row("Fulfiller", req.fulfiller)
            table.add_row("Result", req.result.hex()[:40] + "...")

        console.print(table)
    except Exception as e:
        print_error(f"Failed to get request status: {e}")


@oracle.command("approve-model")
@click.option("--network", default="local", help="Network name")
@click.option("--key", default=None, help="Private key")
@click.argument("model_name")
def oracle_approve_model(network: str, key: Optional[str], model_name: str):
    """Approve a model for inference (admin only)."""
    try:
        client = _get_client(network, key)
        model_hash = Web3.keccak(text=model_name)

        with spinner(f"Approving model '{model_name}'..."):
            tx_hash = client.oracle.approve_model(model_hash)

        print_success(f"Model approved!")
        print_info(f"  Model:      {model_name}")
        print_info(f"  Model Hash: {model_hash.hex()[:20]}...")
        print_info(f"  TX Hash:    {tx_hash}")

        # Verify
        is_approved = client.oracle.is_model_approved(model_hash)
        print_info(f"  Verified:   {is_approved}")
    except Exception as e:
        print_error(f"Approval failed: {e}")
