"""
zkML Verification CLI commands for ModernTensor

Commands:
- status: Show ZkMLVerifier status (dev mode, etc.)
- verify: Submit a zkML proof for verification
- trust-image: Trust a zkML image ID (admin)
- dev-proof: Create and verify a dev-mode proof (testing)
"""

import click
import os
from typing import Optional
from web3 import Web3

from sdk.cli.ui import (
    print_error, print_success, print_info, print_warning,
    console, create_table, print_panel, spinner
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


@click.group(name="zkml", short_help="zkML proof verification")
@click.pass_context
def zkml(ctx):
    """
    zkML — On-chain verification of machine learning proofs.

    Supports STARK (RISC Zero), Groth16, and Dev mode proofs.
    """
    pass


@zkml.command("status")
@click.option("--network", default="local", help="Network name")
@click.option("--key", default=None, help="Private key")
def zkml_status(network: str, key: Optional[str]):
    """Show ZkMLVerifier status and configuration."""
    try:
        client = _get_client(network, key)
        z = client.zkml

        dev_mode = z.dev_mode_enabled()

        table = create_table("ZkML Verifier Status", [
            ("Metric", "cyan"),
            ("Value", "green"),
        ])
        table.add_row("Dev Mode", "✅ Enabled" if dev_mode else "❌ Disabled")
        table.add_row("Contract", str(client._addresses.get("ZkMLVerifier", "N/A")))
        table.add_row("Proof Types", "STARK (0), Groth16 (1), Dev (2)")

        console.print(table)
    except Exception as e:
        print_error(f"Failed to get zkML status: {e}")


@zkml.command("verify")
@click.option("--network", default="local", help="Network name")
@click.option("--key", default=None, help="Private key")
@click.option("--image-id", required=True, help="Image ID (32-byte hex or model name)")
@click.option("--journal", required=True, help="Public journal output")
@click.option("--seal", required=True, help="Proof seal data (hex)")
@click.option("--proof-type", default=2, type=int,
              help="Proof type: 0=STARK, 1=Groth16, 2=Dev")
def zkml_verify(network: str, key: Optional[str], image_id: str,
                journal: str, seal: str, proof_type: int):
    """Verify a zkML proof with explicit parameters."""
    try:
        client = _get_client(network, key)

        # Parse image ID — if it looks like hex, use it directly; else hash it
        if len(image_id) == 64 or image_id.startswith("0x"):
            img_bytes = bytes.fromhex(image_id.removeprefix("0x"))
        else:
            img_bytes = Web3.keccak(text=image_id)

        journal_bytes = journal.encode("utf-8")
        seal_bytes = bytes.fromhex(seal.removeprefix("0x"))

        proof_names = {0: "STARK", 1: "Groth16", 2: "Dev"}
        print_info(f"  Proof type: {proof_names.get(proof_type, str(proof_type))}")

        with spinner("Verifying zkML proof..."):
            tx_hash = client.zkml.verify_proof(
                image_id=img_bytes,
                journal=journal_bytes,
                seal=seal_bytes,
                proof_type=proof_type,
            )

        print_success("Proof verified on-chain!")
        print_info(f"  TX Hash:  {tx_hash}")
        print_info(f"  Image ID: {img_bytes.hex()[:20]}...")
    except Exception as e:
        print_error(f"Verification failed: {e}")


@zkml.command("trust-image")
@click.option("--network", default="local", help="Network name")
@click.option("--key", default=None, help="Private key")
@click.argument("image_name")
def zkml_trust_image(network: str, key: Optional[str], image_name: str):
    """Trust a zkML image ID (admin only)."""
    try:
        client = _get_client(network, key)

        # Hash the image name to get image ID
        image_id = Web3.keccak(text=image_name)

        with spinner(f"Trusting image '{image_name}'..."):
            tx_hash = client.zkml.trust_image(image_id)

        print_success("Image trusted!")
        print_info(f"  Image:    {image_name}")
        print_info(f"  Image ID: {image_id.hex()[:20]}...")
        print_info(f"  TX Hash:  {tx_hash}")

        # Verify
        is_trusted = client.zkml.is_image_trusted(image_id)
        print_info(f"  Verified: {is_trusted}")
    except Exception as e:
        print_error(f"Trust failed: {e}")


@zkml.command("dev-proof")
@click.option("--network", default="local", help="Network name")
@click.option("--key", default=None, help="Private key")
@click.option("--model", default="moderntensor-ai-v1", help="Model name for image ID")
@click.option("--result", "result_data", default="inference:cat:0.97",
              help="Simulated inference result")
def zkml_dev_proof(network: str, key: Optional[str], model: str, result_data: str):
    """Create and verify a dev-mode proof (for testing)."""
    try:
        client = _get_client(network, key)
        z = client.zkml

        # Check dev mode
        if not z.dev_mode_enabled():
            print_warning("Dev mode is disabled. Enable it first.")
            return

        # Create dev proof
        image_id = Web3.keccak(text=model)
        journal = result_data.encode("utf-8")
        seal, proof_hash = z.create_dev_proof(image_id, journal)

        print_info(f"  Model:      {model}")
        print_info(f"  Image ID:   {image_id.hex()[:20]}...")
        print_info(f"  Journal:    {result_data}")
        print_info(f"  Seal:       {seal.hex()[:20]}...")
        print_info(f"  Proof hash: {proof_hash.hex()[:20]}...")

        # Trust image first if needed
        if not z.is_image_trusted(image_id):
            with spinner("Trusting image ID..."):
                z.trust_image(image_id)
            print_success("Image trusted")

        # Verify the proof on-chain
        with spinner("Verifying dev proof on-chain..."):
            tx_hash = z.verify_proof(
                image_id=image_id,
                journal=journal,
                seal=seal,
                proof_type=2,  # DEV
            )

        print_success("Dev proof verified on-chain!")
        print_info(f"  TX Hash: {tx_hash}")
    except Exception as e:
        print_error(f"Dev proof failed: {e}")
