#!/usr/bin/env python3
"""
ModernTensor Miner — Join a subnet and earn MDT rewards.

This script registers as a miner in a subnet, listens for AI inference
tasks from the Oracle, processes them with a model function, generates
zkML proofs, and submits results on-chain.

Usage:
    # With Gemini API (recommended)
    GEMINI_API_KEY=your_key python scripts/run_miner.py --netuid 1 --stake 100

    # With explicit Gemini key
    python scripts/run_miner.py --netuid 1 --gemini-key AIza...

    # With custom model endpoint
    python scripts/run_miner.py --netuid 1 --stake 100 --model-url http://localhost:8000/infer

    # On testnet
    python scripts/run_miner.py --network polkadot_testnet --netuid 1

Environment:
    MINER_PRIVATE_KEY   – Wallet private key (required)
    GEMINI_API_KEY      – Google Gemini API key (recommended for real AI)
    DEPLOYMENT_PATH     – Path to deployments JSON (default: luxtensor/contracts/deployments-polkadot.json)
"""

import argparse
import json
import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web3 import Web3
from sdk.polkadot.client import PolkadotClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-20s │ %(levelname)-5s │ %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("miner")


# ═══════════════════════════════════════════════════════════
# Model Backends
# ═══════════════════════════════════════════════════════════

def make_http_model(url: str):
    """Create a model function that calls an HTTP endpoint."""
    import httpx

    def model_fn(input_data: bytes) -> bytes:
        resp = httpx.post(url, content=input_data, timeout=30.0)
        resp.raise_for_status()
        return resp.content

    return model_fn


def make_fallback_model():
    """Use the SDK's built-in deterministic model (when no API key is set)."""
    from sdk.polkadot.orchestrator import AISubnetOrchestrator
    return lambda input_data: AISubnetOrchestrator._simulate_model("generic-ai", input_data)


def make_gemini_model(api_key: str):
    """Create a model function powered by Google Gemini API."""
    from sdk.polkadot.llm_adapter import LocalLLMAdapter

    adapter = LocalLLMAdapter.from_gemini(api_key=api_key)
    log.info("🤖 Gemini AI model ready: %s", adapter)

    def model_fn(input_data: bytes) -> bytes:
        prompt = input_data.decode("utf-8", errors="replace")
        return adapter.infer(prompt)

    return model_fn


# ═══════════════════════════════════════════════════════════
# Miner Loop
# ═══════════════════════════════════════════════════════════

def run_miner(args):
    """Main miner loop."""
    private_key = os.environ.get("MINER_PRIVATE_KEY", args.private_key)
    if not private_key:
        log.error("Set MINER_PRIVATE_KEY env var or pass --private-key")
        sys.exit(1)

    deploy_path = args.deployment_path or os.environ.get(
        "DEPLOYMENT_PATH", "luxtensor/contracts/deployments-polkadot.json"
    )

    # ── Connect ──
    log.info("Connecting to %s...", args.network)
    client = PolkadotClient(
        network=args.network,
        rpc_url=args.rpc_url,
        private_key=private_key,
        deployment_path=deploy_path,
    )
    log.info("Connected! Chain=%d, Block=%d", client.chain_id, client.block_number)
    log.info("Miner address: %s", client.address)

    balance_mdt = client.token.balance_of_ether()
    balance_native = Web3.from_wei(client.get_eth_balance(), "ether")
    log.info("MDT balance: %s MDT", balance_mdt)
    log.info("Native balance: %s", balance_native)

    # ── Register as miner ──
    netuid = args.netuid
    if not client.subnet.is_registered(netuid):
        log.info("Registering as miner in subnet %d (stake=%s MDT)...", netuid, args.stake)
        try:
            # Approve stake if needed
            if args.stake > 0:
                client.token.approve(
                    client._addresses["SubnetRegistry"],
                    Web3.to_wei(args.stake, "ether"),
                )
            tx = client.subnet.register_miner(
                netuid=netuid,
                stake_ether=args.stake,
            )
            log.info("✅ Registered as miner! TX: %s", tx)
        except Exception as e:
            log.warning("Registration failed (may already be registered): %s", e)
    else:
        log.info("✅ Already registered in subnet %d", netuid)

    # ── Determine UID ──
    try:
        meta = client.subnet.get_metagraph(netuid)
        my_node = None
        for n in meta.nodes:
            if n.hotkey.lower() == client.address.lower():
                my_node = n
                break
        if my_node:
            log.info("Miner UID: %d, Stake: %s MDT", my_node.uid, my_node.total_stake_ether)
        else:
            log.info("Node not found in metagraph yet")
    except Exception as e:
        log.warning("Could not fetch metagraph: %s", e)

    # ── Setup model ──
    if args.model_url:
        log.info("Using HTTP model endpoint: %s", args.model_url)
        model_fn = make_http_model(args.model_url)
    elif args.gemini_key or os.environ.get("GEMINI_API_KEY"):
        gemini_key = args.gemini_key or os.environ.get("GEMINI_API_KEY")
        log.info("🤖 Using Google Gemini API for real AI inference")
        model_fn = make_gemini_model(gemini_key)
    else:
        log.info("Using built-in deterministic model (set GEMINI_API_KEY for real AI)")
        model_fn = make_fallback_model()

    # ── Create orchestrator ──
    orchestrator = client.orchestrator(netuid=netuid)

    # ── Main loop: Listen for AI requests ──
    log.info("═" * 60)
    log.info("⛏️  MINER RUNNING — Listening for AI tasks on subnet %d", netuid)
    log.info("═" * 60)
    log.info("Poll interval: %ds", args.poll_interval)

    last_block = client.block_number
    tasks_completed = 0

    while True:
        try:
            current_block = client.block_number

            if current_block > last_block:
                # Poll for new AI requests
                events = client.events.get_ai_requests(
                    from_block=last_block + 1,
                    to_block=current_block,
                )

                for event in events:
                    request_id = event.get("requestId", b"")
                    model_hash = event.get("modelHash", b"")
                    log.info(
                        "📥 New task! requestId=%s, model=%s",
                        request_id.hex()[:16] if isinstance(request_id, bytes) else str(request_id)[:16],
                        model_hash.hex()[:16] if isinstance(model_hash, bytes) else str(model_hash)[:16],
                    )

                    # Fetch full request details
                    try:
                        req = client.oracle.get_request(request_id)
                        if not req.is_pending:
                            log.info("  → Already fulfilled/expired, skipping")
                            continue

                        # Process the task with our model
                        log.info("  → Processing with model... (reward=%s)", req.reward_ether)
                        output = model_fn(req.input_data)
                        log.info("  → Model output: %d bytes", len(output))

                        # Generate zkML proof
                        image_id = model_hash if isinstance(model_hash, bytes) else bytes.fromhex(model_hash)
                        seal, proof_hash = client.zkml.create_dev_proof(image_id, output)
                        log.info("  → zkML proof generated: %s", proof_hash.hex()[:16])

                        # Submit proof to verifier
                        try:
                            client.zkml.verify_proof(
                                image_id=image_id,
                                journal=output,
                                seal=seal,
                                proof_type=2,  # DEV mode
                            )
                            log.info("  → Proof verified on-chain ✅")
                        except Exception as e:
                            log.warning("  → Proof verification failed: %s", e)

                        # Fulfill the oracle request
                        try:
                            tx = client.oracle.fulfill_request(
                                request_id=request_id,
                                result=output,
                                proof_hash=proof_hash,
                            )
                            tasks_completed += 1
                            log.info(
                                "  → ✅ Task fulfilled! TX: %s (total: %d)",
                                tx[:16], tasks_completed,
                            )
                        except Exception as e:
                            log.warning("  → Fulfill failed: %s", e)

                    except Exception as e:
                        log.warning("  → Error processing task: %s", e)

                last_block = current_block

            # Heartbeat
            if tasks_completed > 0 or current_block % 50 == 0:
                log.debug(
                    "Block %d | Tasks completed: %d",
                    current_block, tasks_completed,
                )

        except KeyboardInterrupt:
            log.info("🛑 Miner stopped by user")
            break
        except Exception as e:
            log.error("Loop error: %s", e)

        time.sleep(args.poll_interval)

    log.info("Total tasks completed: %d", tasks_completed)


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="ModernTensor Miner — Earn MDT rewards by processing AI tasks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick start with Gemini API (recommended)
  GEMINI_API_KEY=AIza... MINER_PRIVATE_KEY=0x... python scripts/run_miner.py --netuid 1

  # With explicit key
  python scripts/run_miner.py --netuid 1 --gemini-key AIza...

  # With custom HTTP model
  MINER_PRIVATE_KEY=0x... python scripts/run_miner.py --netuid 1 --model-url http://localhost:8000/infer

  # Local Hardhat testing
  python scripts/run_miner.py --network localhost --netuid 1 --private-key 0x59c6995e...
        """,
    )
    parser.add_argument("--network", default="polkadot_testnet", help="Network name (default: polkadot_testnet)")
    parser.add_argument("--rpc-url", default=None, help="Override RPC URL")
    parser.add_argument("--netuid", type=int, default=1, help="Subnet UID to mine on (default: 1)")
    parser.add_argument("--stake", type=float, default=0, help="MDT to stake on registration (default: 0)")
    parser.add_argument("--model-url", default=None, help="HTTP endpoint for AI model")
    parser.add_argument("--gemini-key", default=None, help="Google Gemini API key (or set GEMINI_API_KEY env)")
    parser.add_argument("--poll-interval", type=int, default=3, help="Seconds between polls (default: 3)")
    parser.add_argument("--private-key", default=None, help="Private key (prefer MINER_PRIVATE_KEY env var)")
    parser.add_argument("--deployment-path", default=None, help="Path to deployments JSON")

    args = parser.parse_args()
    run_miner(args)


if __name__ == "__main__":
    main()
