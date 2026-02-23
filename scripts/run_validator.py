#!/usr/bin/env python3
"""
ModernTensor Validator — Orchestrate a subnet and distribute rewards.

This script registers as a validator, creates AI inference tasks,
evaluates miner results with quality scoring + zkML proof verification,
sets weights via commit-reveal, and triggers emission epochs.

Usage:
    # Start validating subnet 1
    python scripts/run_validator.py --netuid 1 --stake 500

    # With custom task domain
    python scripts/run_validator.py --netuid 1 --domain code-review --payment 0.05

    # Local testing
    python scripts/run_validator.py --network localhost --netuid 1

Environment:
    VALIDATOR_PRIVATE_KEY  – Wallet private key (required)
    DEPLOYMENT_PATH        – Path to deployments JSON
"""

import argparse
import json
import logging
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web3 import Web3
from sdk.polkadot.client import PolkadotClient
from sdk.polkadot.orchestrator import AISubnetOrchestrator, MinerResult

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-20s │ %(levelname)-5s │ %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("validator")


# ═══════════════════════════════════════════════════════════
# Task Templates
# ═══════════════════════════════════════════════════════════

TASK_TEMPLATES = {
    "nlp": [
        b"Analyze the sentiment of: ModernTensor provides decentralized AI services on Polkadot",
        b"Summarize: The zkML verification ensures that AI model computations are provably correct",
        b"Classify this text: Staking MDT tokens allows participation in subnet governance",
    ],
    "code-review": [
        b"Review the following Solidity function for vulnerabilities:\nfunction withdraw(uint amount) external { payable(msg.sender).transfer(amount); }",
        b"Analyze this smart contract pattern for reentrancy risks:\nfunction swap(address token, uint amount) external nonReentrant { IERC20(token).transfer(msg.sender, amount); }",
        b"Check for access control issues:\nfunction setAdmin(address newAdmin) external { admin = newAdmin; }",
    ],
    "finance": [
        b"Assess risk score for portfolio: 40% BTC, 30% DOT, 20% ETH, 10% stablecoins",
        b"Analyze market correlation between DOT and KSM over 30-day window",
        b"Predict liquidation risk for a 2x leveraged position in current market conditions",
    ],
    "health": [
        b"Classify symptoms: headache, fatigue, mild fever — suggest urgency level",
        b"Analyze drug interaction potential: aspirin + warfarin",
        b"Risk assessment for patient profile: age=45, BMI=28, smoking=no, exercise=moderate",
    ],
    "generic": [
        b"Process this general inference request with the AI model",
        b"Generate a structured analysis report for this input data",
        b"Perform multi-dimensional quality assessment on the provided dataset",
    ],
}


# ═══════════════════════════════════════════════════════════
# Validator Loop
# ═══════════════════════════════════════════════════════════

def run_validator(args):
    """Main validator loop."""
    private_key = os.environ.get("VALIDATOR_PRIVATE_KEY", args.private_key)
    if not private_key:
        log.error("Set VALIDATOR_PRIVATE_KEY env var or pass --private-key")
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
    log.info("Validator address: %s", client.address)

    balance_mdt = client.token.balance_of_ether()
    balance_native = Web3.from_wei(client.get_eth_balance(), "ether")
    log.info("MDT balance: %s MDT", balance_mdt)
    log.info("Native balance: %s", balance_native)

    # ── Register as validator ──
    netuid = args.netuid
    if not client.subnet.is_registered(netuid):
        log.info("Registering as validator in subnet %d (stake=%s MDT)...", netuid, args.stake)
        try:
            if args.stake > 0:
                client.token.approve(
                    client._addresses["SubnetRegistry"],
                    Web3.to_wei(args.stake, "ether"),
                )
            tx = client.subnet.register_validator(
                netuid=netuid,
                stake_ether=args.stake,
            )
            log.info("✅ Registered as validator! TX: %s", tx)
        except Exception as e:
            log.warning("Registration failed (may already be registered): %s", e)
    else:
        log.info("✅ Already registered in subnet %d", netuid)

    # ── Get metagraph ──
    orchestrator = client.orchestrator(netuid=netuid)

    log.info("═" * 60)
    log.info("🔍 VALIDATOR RUNNING — Orchestrating subnet %d", netuid)
    log.info("═" * 60)
    log.info("Domain: %s | Epoch interval: %ds | Payment: %s",
             args.domain, args.epoch_interval, args.payment)

    epoch = 0

    while True:
        try:
            epoch += 1
            log.info("━" * 50)
            log.info("📋 EPOCH %d — Block %d", epoch, client.block_number)
            log.info("━" * 50)

            # ── Step 1: Refresh metagraph ──
            try:
                meta = client.subnet.get_metagraph(netuid)
                miners = meta.miners
                validators = meta.validators
                log.info(
                    "Metagraph: %d miners, %d validators, total_stake=%s MDT",
                    len(miners), len(validators),
                    Web3.from_wei(meta.total_stake, "ether"),
                )
            except Exception as e:
                log.warning("Metagraph fetch failed: %s", e)
                miners = []

            if not miners:
                log.info("No active miners — waiting for registrations...")
                time.sleep(args.epoch_interval)
                continue

            # ── Step 2: Create inference tasks ──
            domain = args.domain
            templates = TASK_TEMPLATES.get(domain, TASK_TEMPLATES["generic"])
            task_input = random.choice(templates)
            model_name = f"{domain}-v1"

            log.info("Creating task: model=%s, input=%d bytes", model_name, len(task_input))

            try:
                task = orchestrator.create_inference_task(
                    model_name=model_name,
                    input_data=task_input,
                    payment_ether=args.payment,
                    timeout=args.task_timeout,
                )
                log.info("✅ Task created: id=%s, tx=%s", task.task_id, task.oracle_tx[:16])
            except Exception as e:
                log.error("Task creation failed: %s", e)
                time.sleep(args.epoch_interval)
                continue

            # ── Step 3: Wait for miners to process ──
            log.info("⏳ Waiting %ds for miner responses...", args.response_wait)
            time.sleep(args.response_wait)

            # ── Step 4: Collect fulfilled results ──
            log.info("Checking for fulfilled results...")
            fulfilled_events = client.events.get_fulfilled_requests(
                from_block=max(0, client.block_number - 100),
            )
            log.info("Found %d fulfilled requests", len(fulfilled_events))

            # Build MinerResults for evaluation
            miner_results: list[MinerResult] = []
            for event in fulfilled_events:
                try:
                    fulfiller = event.get("fulfiller", "")
                    # Find miner UID
                    miner_uid = 0
                    for m in miners:
                        if m.hotkey.lower() == fulfiller.lower():
                            miner_uid = m.uid
                            break

                    result_data = event.get("result", b"")
                    proof_hash = event.get("proofHash", b"\x00" * 32)

                    miner_results.append(MinerResult(
                        miner_address=fulfiller,
                        miner_uid=miner_uid,
                        task_id=task.task_id,
                        output=result_data if isinstance(result_data, bytes) else result_data.encode(),
                        proof_hash=proof_hash,
                        proof_verified=proof_hash != b"\x00" * 32,
                        quality_score=0.0,
                    ))
                except Exception as e:
                    log.warning("Error parsing result: %s", e)

            if not miner_results:
                log.info("No fulfilled results this epoch — miners may still be processing")

                # If no real results, evaluate active miners with simulated scores
                if args.simulate_eval and miners:
                    log.info("Simulating evaluation for %d active miners...", len(miners))
                    for m in miners:
                        sim_output = AISubnetOrchestrator._simulate_model(
                            model_name, task_input,
                        )
                        miner_results.append(MinerResult(
                            miner_address=m.hotkey,
                            miner_uid=m.uid,
                            task_id=task.task_id,
                            output=sim_output,
                            proof_verified=True,
                        ))

            # ── Step 5: Evaluate and set weights ──
            if miner_results:
                log.info("Evaluating %d miner results...", len(miner_results))
                try:
                    eval_result = orchestrator.evaluate_miners(miner_results)
                    log.info(
                        "✅ Weights set! TX=%s | Avg quality=%.2f | Verified=%d/%d",
                        eval_result.weights_set_tx[:16] if eval_result.weights_set_tx else "N/A",
                        eval_result.average_quality,
                        eval_result.verified_proofs,
                        eval_result.total_tasks,
                    )
                    for uid, score in eval_result.miner_scores.items():
                        log.info("  Miner UID %d: score=%.3f", uid, score)
                except Exception as e:
                    log.error("Evaluation/weight-setting failed: %s", e)

            # ── Step 6: Trigger epoch (emission) ──
            if args.run_epoch:
                try:
                    epoch_tx = client.subnet.run_epoch(netuid)
                    log.info("🏆 Epoch emission distributed! TX: %s", epoch_tx[:16])
                except Exception as e:
                    log.debug("Epoch not ready yet: %s", e)

            # ── Status ──
            log.info(
                "Epoch %d complete | Block: %d | Next epoch in %ds",
                epoch, client.block_number, args.epoch_interval,
            )

        except KeyboardInterrupt:
            log.info("🛑 Validator stopped by user")
            break
        except Exception as e:
            log.error("Epoch error: %s", e)

        time.sleep(args.epoch_interval)

    log.info("Total epochs run: %d", epoch)


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="ModernTensor Validator — Orchestrate AI tasks and distribute rewards",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start validating subnet 1 with NLP tasks
  VALIDATOR_PRIVATE_KEY=0x... python scripts/run_validator.py --netuid 1 --domain nlp

  # Code review subnet
  VALIDATOR_PRIVATE_KEY=0x... python scripts/run_validator.py --netuid 2 --domain code-review

  # Local Hardhat testing
  python scripts/run_validator.py --network localhost --netuid 1 --private-key 0xac0974...
        """,
    )
    parser.add_argument("--network", default="polkadot_testnet", help="Network name")
    parser.add_argument("--rpc-url", default=None, help="Override RPC URL")
    parser.add_argument("--netuid", type=int, default=1, help="Subnet UID (default: 1)")
    parser.add_argument("--stake", type=float, default=0, help="MDT to stake (default: 0)")
    parser.add_argument("--domain", default="nlp", choices=list(TASK_TEMPLATES.keys()),
                        help="AI domain for tasks (default: nlp)")
    parser.add_argument("--payment", type=float, default=0.01, help="Payment per task in native token")
    parser.add_argument("--epoch-interval", type=int, default=30, help="Seconds between epochs (default: 30)")
    parser.add_argument("--response-wait", type=int, default=15, help="Seconds to wait for miner responses")
    parser.add_argument("--task-timeout", type=int, default=100, help="Task timeout in blocks")
    parser.add_argument("--run-epoch", action="store_true", help="Trigger emission epoch after each cycle")
    parser.add_argument("--simulate-eval", action="store_true", default=True,
                        help="Simulate evaluation if no real miner responses (default: true)")
    parser.add_argument("--no-simulate-eval", dest="simulate_eval", action="store_false")
    parser.add_argument("--private-key", default=None, help="Private key (prefer VALIDATOR_PRIVATE_KEY env)")
    parser.add_argument("--deployment-path", default=None, help="Path to deployments JSON")

    args = parser.parse_args()
    run_validator(args)


if __name__ == "__main__":
    main()
