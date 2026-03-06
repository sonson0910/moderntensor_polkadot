#!/usr/bin/env python3
"""
ModernTensor Demo — Step 6: Run Validator

A complete validator node that:
  1. Creates AI inference tasks across multiple domains
  2. Orchestrates miner task processing
  3. Evaluates miner results (quality + proof verification)
  4. Sets weights using commit-reveal scheme
  5. Triggers epoch emission
  6. Claims rewards
  7. Displays metagraph

Usage:
  python demo/06_run_validator.py
  NETWORK=polkadot_testnet NETUID=1 python demo/06_run_validator.py
"""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from demo.config import (
    get_network,
    HARDHAT_ACCOUNTS,
    AI_MODELS,
    banner,
    step_log,
    ok,
    info,
    warn,
    separator,
)
from web3 import Web3


# ═══════════════════════════════════════════════════════════
# Validator Node
# ═══════════════════════════════════════════════════════════
class ValidatorNode:
    """
    Complete validator node for ModernTensor subnet.
    Handles: task creation, evaluation, weight setting, epochs.
    """

    # Task definitions for multi-domain AI inference
    TASKS = [
        {
            "model": "nlp-sentiment-v1",
            "label": "NLP Sentiment Analysis",
            "input": b"Analyze sentiment: ModernTensor brings decentralized AI to Polkadot. "
            b"The protocol enables permissionless innovation across NLP, Finance, Code Review.",
            "payment": 0.01,
        },
        {
            "model": "finance-risk-v1",
            "label": "Financial Risk Assessment",
            "input": b"Assess DeFi portfolio risk: ETH=40%, BTC=30%, MDT=20%, stablecoins=10%. "
            b"Total value: $150k. Leverage: 1.5x. Duration: 90 days.",
            "payment": 0.008,
        },
        {
            "model": "code-review-v1",
            "label": "Smart Contract Audit",
            "input": b"Review: function transfer(address to, uint256 amount) external { "
            b"balances[msg.sender] -= amount; balances[to] += amount; }",
            "payment": 0.01,
        },
    ]

    def __init__(self, client, netuid=1):
        self.client = client
        self.netuid = netuid
        self.uid = client.subnet.get_uid(netuid, client.address)
        self.orch = client.orchestrator(netuid=netuid, validator_uid=self.uid)
        self.rounds_completed = 0

    def create_tasks(self):
        """Create AI inference tasks across multiple domains."""
        banner("CREATE AI INFERENCE TASKS")

        tasks = []
        for i, task_def in enumerate(self.TASKS):
            step_log(
                f"T{i+1}",
                f"[{task_def['label']}] Creating task...",
            )

            task = self.orch.create_inference_task(
                model_name=task_def["model"],
                input_data=task_def["input"],
                payment_ether=task_def["payment"],
            )

            ok(f"Task ID: {task.task_id}")
            ok(f"  Model: {task.model_name}")
            ok(f"  Oracle TX: {task.oracle_tx}")
            tasks.append(task)

        info(f"Created {len(tasks)} tasks across {len(tasks)} AI domains")
        return tasks

    def process_tasks_with_miner(self, tasks, miner_node):
        """Have the miner process all tasks."""
        banner("MINER PROCESSES TASKS")

        results = []
        for i, task in enumerate(tasks):
            step_log(f"P{i+1}", f"Miner processing: {task.model_name}...")

            result = miner_node.process_task_from_orchestrator(task, self.orch)

            ok(f"Output: {result.output[:60].decode('utf-8', errors='replace')}...")
            ok(f"  Proof verified: {result.proof_verified}")
            ok(f"  Quality: {result.quality_score:.0%}")
            results.append(result)

        verified = sum(1 for r in results if r.proof_verified)
        info(f"Summary: {verified}/{len(results)} proofs verified")

        return results

    def evaluate_and_set_weights(self, results):
        """Evaluate miner performance and set weights on-chain."""
        banner("EVALUATE & SET WEIGHTS")

        step_log("E1", "Evaluating miner results...")
        evaluation = self.orch.evaluate_miners(results)

        ok(f"Tasks evaluated: {evaluation.total_tasks}")
        ok(f"  Verified proofs: {evaluation.verified_proofs}/{evaluation.total_tasks}")
        ok(f"  Average quality: {evaluation.average_quality:.2%}")

        step_log("E2", "Weights set on-chain...")
        ok(f"Weights TX: {evaluation.weights_set_tx}")

        for uid, score in evaluation.miner_scores.items():
            weight = int(score * 10000)
            ok(f"  Miner UID {uid} → weight {weight} (score: {score:.2%})")

        # Verify stored weights
        uids, weights = self.client.subnet.get_weights(self.netuid, self.uid)
        info(f"  On-chain weights: UIDs={uids}, Weights={weights}")

        return evaluation

    def run_epoch(self, w3=None):
        """Mine blocks and run epoch for emission distribution."""
        banner("RUN EPOCH (Yuma Consensus Emission)")

        owner_client = self.client  # Typically needs owner client

        # Mine blocks to exceed tempo
        step_log("EP1", "Mining blocks to exceed tempo period...")
        if w3:
            blocks_to_mine = 15  # Small for demo (tempo=10)
            for _ in range(blocks_to_mine):
                w3.provider.make_request("evm_mine", [])
            ok(f"Mined {blocks_to_mine} blocks. Current: {w3.eth.block_number}")

        # Run epoch
        step_log("EP2", "Running epoch (emission distribution)...")
        try:
            tx = owner_client.subnet.run_epoch(self.netuid)
            ok(f"Epoch complete! TX: {tx}")

            sn = owner_client.subnet.get_subnet(self.netuid)
            info(f"  Subnet: {sn.name}")
            info(f"  Emission share: {sn.emission_percent:.1f}%")
            self.rounds_completed += 1
        except Exception as e:
            info(f"Epoch note: {str(e)[:100]}")

    def claim_rewards(self, miner_uid=None):
        """Claim emission rewards for validator and optionally miner."""
        banner("CLAIM EMISSION REWARDS")

        # Validator claim
        step_log("C1", "Checking validator pending emission...")
        val_node = self.client.subnet.get_node(self.netuid, self.uid)
        ok(f"Validator pending: {val_node.emission_ether:.6f} MDT")

        if val_node.emission > 0:
            try:
                tx = self.client.subnet.claim_emission(self.netuid, self.uid)
                ok(f"Validator claimed! TX: {tx}")
            except Exception as e:
                info(f"Claim: {str(e)[:80]}")

        return val_node.emission_ether

    def display_metagraph(self):
        """Display the current subnet metagraph."""
        banner("SUBNET METAGRAPH")

        meta = self.client.subnet.get_metagraph(self.netuid)

        print(f"\n  📊 Subnet {self.netuid}")
        separator()
        print(
            f"  {'UID':<5} {'Type':<12} {'Hotkey':<16} "
            f"{'Stake':<14} {'Rank':<12} {'Emission':<12} {'Active'}"
        )
        separator()

        for node in meta.nodes:
            node_type = "VALIDATOR" if node.is_validator else "MINER"
            print(
                f"  {node.uid:<5} {node_type:<12} {node.hotkey[:14]}.. "
                f"{node.total_stake_ether:<14.4f} {node.rank_float:<12.6f} "
                f"{node.emission_ether:<12.6f} {'Yes' if node.active else 'No'}"
            )

        separator()
        total = Web3.from_wei(meta.total_stake, "ether")
        print(
            f"  Total Stake: {total} MDT | "
            f"Miners: {len(meta.miners)} | Validators: {len(meta.validators)}"
        )

    def status(self):
        """Print validator status."""
        node = self.client.subnet.get_node(self.netuid, self.uid)
        separator()
        print(f"  🔷 Validator Status")
        print(f"  UID:              {self.uid}")
        print(f"  Address:          {self.client.address}")
        print(f"  Stake:            {node.total_stake_ether:.2f} MDT")
        print(f"  Active:           {node.active}")
        print(f"  Rounds Completed: {self.rounds_completed}")
        print(f"  Pending Emission: {node.emission_ether:.6f} MDT")
        separator()


def main():
    print("\n🔷 ModernTensor — Validator Node")
    print("   Task creation, evaluation, weight setting\n")

    network_name = os.environ.get("NETWORK", "local")
    netuid = int(os.environ.get("NETUID", "1"))

    from sdk.polkadot.client import PolkadotClient

    net = get_network(network_name)
    wallets = HARDHAT_ACCOUNTS if network_name == "local" else None

    if wallets is None:
        import json

        wallet_file = Path(__file__).resolve().parent / "wallets.json"
        with open(wallet_file) as f:
            wallets = json.load(f)

    # Create clients
    val_client = PolkadotClient(
        rpc_url=net["rpc_url"],
        private_key=wallets["validator"]["key"],
        deployment_path=net["deployment"],
    )

    ok(f"Connected: {net['label']}")
    ok(f"Validator: {val_client.address}")

    # Verify registration
    if not val_client.subnet.is_registered(netuid, val_client.address):
        from demo.config import fail

        fail("Validator not registered! Run: python demo/04_register_subnet.py")

    # Create and show status
    validator = ValidatorNode(val_client, netuid=netuid)
    validator.status()

    # Standalone mode: create tasks and wait for miner
    info("Validator running. Create tasks with: python demo/07_run_demo.py")


if __name__ == "__main__":
    main()
