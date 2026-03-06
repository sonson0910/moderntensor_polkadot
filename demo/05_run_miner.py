#!/usr/bin/env python3
"""
ModernTensor Demo — Step 5: Run Miner

A complete miner node that:
  1. Connects to the subnet
  2. Listens for AI inference tasks from the Oracle
  3. Processes inference requests (simulated or via API)
  4. Generates zkML proofs of computation
  5. Submits results to the Oracle
  6. Participates in federated learning rounds
  7. Claims emission rewards

Usage:
  python demo/05_run_miner.py
  NETWORK=polkadot_testnet NETUID=1 python demo/05_run_miner.py
"""

import os
import sys
import time
import hashlib
import signal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from demo.config import (
    get_network,
    HARDHAT_ACCOUNTS,
    banner,
    step_log,
    ok,
    info,
    warn,
    separator,
)
from web3 import Web3


# ═══════════════════════════════════════════════════════════
# AI Model Inference Engine (Simulated for Demo)
# ═══════════════════════════════════════════════════════════
class AIModelEngine:
    """
    Simulated AI inference engine for demo purposes.
    In production, replace with real model serving (ONNX, TensorFlow, etc.)
    """

    MODELS = {
        "nlp-sentiment-v1": {
            "domain": "NLP",
            "task": "Sentiment Analysis",
            "response_template": (
                "Sentiment Analysis Result:\n"
                "- Overall Sentiment: POSITIVE (0.87)\n"
                "- Confidence: HIGH\n"
                "- Key phrases: 'decentralized AI', 'permissionless innovation'\n"
                "- Emotional tone: Optimistic, Forward-looking\n"
                "- Domain tags: [technology, blockchain, AI]"
            ),
        },
        "finance-risk-v1": {
            "domain": "Finance",
            "task": "Risk Assessment",
            "response_template": (
                "Risk Assessment Report:\n"
                "- Portfolio Risk Score: 6.2/10 (MODERATE)\n"
                "- Diversification: FAIR (HHI=0.29)\n"
                "- Leverage Risk: ELEVATED (1.5x)\n"
                "- VaR (95%, 1-day): -$4,200 (-2.8%)\n"
                "- Recommendations: Reduce ETH concentration, increase stablecoins to 20%"
            ),
        },
        "code-review-v1": {
            "domain": "Code",
            "task": "Smart Contract Audit",
            "response_template": (
                "Smart Contract Audit:\n"
                "- Severity: HIGH RISK\n"
                "- Issue: Unchecked underflow in transfer()\n"
                "- Line: balances[msg.sender] -= amount\n"
                "- Fix: Use SafeMath or Solidity 0.8+ checks\n"
                "- Additional: Missing zero-address check, no event emission"
            ),
        },
    }

    @classmethod
    def infer(cls, model_name, input_data):
        """Run AI inference on input data."""
        # Strip prefix if present
        short_name = model_name.replace("moderntensor-", "")

        model = cls.MODELS.get(short_name, cls.MODELS.get("nlp-sentiment-v1"))
        response = model["response_template"]

        # Add input context to make it unique
        input_hash = hashlib.sha256(input_data).hexdigest()[:8]
        response += f"\n- Input hash: {input_hash}"
        response += f"\n- Model: {model_name}"
        response += f"\n- Timestamp: {int(time.time())}"

        return response.encode("utf-8")


# ═══════════════════════════════════════════════════════════
# Miner Node
# ═══════════════════════════════════════════════════════════
class MinerNode:
    """
    Complete miner node for ModernTensor subnet.
    Handles: task polling, inference, proof generation, result submission.
    """

    def __init__(self, client, netuid=1, poll_interval=3.0):
        self.client = client
        self.netuid = netuid
        self.poll_interval = poll_interval
        self.running = False
        self.tasks_processed = 0
        self.proofs_generated = 0
        self.earnings = 0.0

        # Get miner UID
        self.uid = client.subnet.get_uid(netuid, client.address)
        self.engine = AIModelEngine()

    def process_pending_tasks(self):
        """Check Oracle for pending requests and process them."""
        oracle = self.client.oracle
        total = oracle.total_requests()

        if total == 0:
            return 0

        processed = 0
        for req_id_int in range(total):
            try:
                # Build request ID from index
                request_id = Web3.keccak(Web3.solidity_keccak(["uint256"], [req_id_int]))

                request = oracle.get_request(request_id)

                # Skip if not pending (status 0)
                if request.status != 0:
                    continue

                # Process the task
                info(f"Processing request (input: {request.input_data[:30]}...)")

                # Run inference
                result = self.engine.infer("nlp-sentiment-v1", request.input_data)

                # Generate zkML proof
                image_id = request.model_hash
                journal = Web3.keccak(result)
                import warnings

                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    seal, proof_hash = self.client.zkml.create_dev_proof(image_id, journal)

                # Verify proof on-chain
                self.client.zkml.verify_proof(
                    image_id=image_id,
                    journal=journal,
                    seal=seal,
                    proof_type=2,  # DEV mode
                )

                # Fulfill request
                tx = oracle.fulfill_request(
                    request_id=request_id,
                    result=result,
                    proof_hash=proof_hash,
                )

                ok(f"Task fulfilled — TX: {tx}")
                self.tasks_processed += 1
                self.proofs_generated += 1
                processed += 1

            except Exception:
                continue

        return processed

    def process_task_from_orchestrator(self, task, orch):
        """Process a task received from the orchestrator."""
        info(f"Processing task: {task.task_id} ({task.model_name})")

        # Run inference
        result_data = self.engine.infer(task.model_name, task.input_data)

        # Generate zkML proof
        image_id = task.model_hash
        journal = Web3.keccak(result_data)
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            seal, proof_hash = self.client.zkml.create_dev_proof(image_id, journal)

        # Verify proof on-chain
        try:
            self.client.zkml.verify_proof(
                image_id=image_id,
                journal=journal,
                seal=seal,
                proof_type=2,  # DEV mode
            )
            ok(f"zkML proof verified on-chain")
        except Exception as e:
            info(f"Proof verification: {str(e)[:60]}")

        # Fulfill Oracle request
        try:
            tx = self.client.oracle.fulfill_request(
                request_id=task.request_id,
                result=result_data,
                proof_hash=proof_hash,
            )
            ok(f"Oracle fulfilled — TX: {tx}")
        except Exception as e:
            info(f"Oracle fulfillment: {str(e)[:60]}")

        self.tasks_processed += 1
        self.proofs_generated += 1

        # Build result object
        from sdk.polkadot.orchestrator import MinerResult

        return MinerResult(
            miner_address=self.client.address,
            miner_uid=self.uid,
            task_id=task.task_id,
            output=result_data,
            seal=seal,
            proof_hash=proof_hash,
            proof_verified=True,
            quality_score=0.85,
            oracle_tx=tx if "tx" in dir() else "",
        )

    def claim_rewards(self):
        """Claim any pending emission rewards."""
        try:
            node = self.client.subnet.get_node(self.netuid, self.uid)
            if node.emission > 0:
                tx = self.client.subnet.claim_emission(self.netuid, self.uid)
                earned = node.emission_ether
                self.earnings += earned
                ok(f"Claimed {earned:.6f} MDT — TX: {tx}")
                return earned
        except Exception as e:
            info(f"Claim: {str(e)[:60]}")
        return 0.0

    def status(self):
        """Print miner status."""
        node = self.client.subnet.get_node(self.netuid, self.uid)
        separator()
        print(f"  ⛏️  Miner Status")
        print(f"  UID:              {self.uid}")
        print(f"  Address:          {self.client.address}")
        print(f"  Stake:            {node.total_stake_ether:.2f} MDT")
        print(f"  Active:           {node.active}")
        print(f"  Tasks Processed:  {self.tasks_processed}")
        print(f"  Proofs Generated: {self.proofs_generated}")
        print(f"  Pending Emission: {node.emission_ether:.6f} MDT")
        print(f"  Total Earnings:   {self.earnings:.6f} MDT")
        separator()

    def run_loop(self, max_rounds=None):
        """Main miner loop — poll for tasks."""
        self.running = True
        rounds = 0

        banner(f"MINER NODE RUNNING (UID={self.uid})")
        self.status()

        while self.running:
            try:
                processed = self.process_pending_tasks()
                if processed > 0:
                    ok(f"Processed {processed} tasks")

                rounds += 1
                if max_rounds and rounds >= max_rounds:
                    info(f"Max rounds ({max_rounds}) reached")
                    break

                time.sleep(self.poll_interval)

            except KeyboardInterrupt:
                info("Miner shutting down...")
                break

        self.claim_rewards()
        self.status()

    def stop(self):
        """Stop the miner loop."""
        self.running = False


def main():
    print("\n⛏️  ModernTensor — Miner Node")
    print("   AI inference + zkML proof generation\n")

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

    client = PolkadotClient(
        rpc_url=net["rpc_url"],
        private_key=wallets["miner"]["key"],
        deployment_path=net["deployment"],
    )

    ok(f"Connected: {net['label']}")
    ok(f"Address: {client.address}")

    # Verify registration
    if not client.subnet.is_registered(netuid, client.address):
        from demo.config import fail

        fail("Miner not registered! Run: python demo/04_register_subnet.py")

    # Create and run miner
    miner = MinerNode(client, netuid=netuid)
    miner.status()

    # In standalone mode, run polling loop
    max_rounds = int(os.environ.get("MAX_ROUNDS", "0")) or None
    info("Press Ctrl+C to stop")
    miner.run_loop(max_rounds=max_rounds)


if __name__ == "__main__":
    main()
