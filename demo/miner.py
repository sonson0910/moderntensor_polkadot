#!/usr/bin/env python3
"""
ModernTensor Miner — Polkadot Hub Testnet

Runs a miner node that:
  1. WAITS for inference tasks from validators (via shared task queue)
  2. Processes received tasks with AI models
  3. Generates zkML proofs of computation
  4. Returns results to the validator
  5. Claims emission rewards after epochs

Flow:  Validator creates task → Miner picks up → Process → Return result

Usage:
  python demo/miner.py                    # Run as miner 1
  MINER_ID=2 python demo/miner.py        # Run as miner 2
  MAX_ROUNDS=10 python demo/miner.py     # Stop after 10 tasks

Press Ctrl+C to stop the miner gracefully.
"""

import os
import sys
import time
import json
import random
import hashlib
import signal
import glob
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web3 import Web3

# ═══════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEPLOYMENT = str(PROJECT_ROOT / "luxtensor" / "contracts" / "deployments-polkadot.json")
WALLET_FILE = Path(__file__).resolve().parent / "wallets.json"
TASK_DIR = Path(__file__).resolve().parent / "task_queue"
RPC_URL = "https://services.polkadothub-rpc.com/testnet"
NETUID = int(os.environ.get("NETUID", "1"))
MINER_ID = int(os.environ.get("MINER_ID", "1"))
POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL", "3"))


# ═══════════════════════════════════════════════════════════
# AI Inference Engine
# ═══════════════════════════════════════════════════════════
def run_inference(model_domain, input_data):
    """Run AI model inference on input data."""
    # Simulate realistic compute time
    compute_time = random.uniform(0.8, 2.5)
    time.sleep(compute_time)

    input_hash = hashlib.sha256(input_data.encode()).hexdigest()[:16]
    confidence = random.uniform(0.78, 0.98)

    results = {
        "NLP": {
            "output": f"Sentiment: {'POSITIVE' if confidence > 0.85 else 'NEUTRAL'} ({confidence:.2f})",
            "details": [
                f"Key phrases: decentralized, AI, blockchain",
                f"Emotional tone: {'Optimistic' if confidence > 0.85 else 'Neutral'}",
                f"Domain tags: [technology, web3, AI]",
            ],
        },
        "Finance": {
            "output": f"Risk Score: {random.uniform(3, 8):.1f}/10 ({'HIGH' if confidence < 0.85 else 'MODERATE'})",
            "details": [
                f"VaR (95%, 1-day): -${random.randint(2000, 6000):,}",
                f"Diversification: {'FAIR' if confidence > 0.85 else 'POOR'} (HHI={random.uniform(0.2, 0.4):.2f})",
                f"Recommendation: {'Hold' if confidence > 0.85 else 'Reduce leverage'}",
            ],
        },
        "Code": {
            "output": f"Severity: {'CRITICAL' if confidence < 0.82 else 'MEDIUM'} — {random.choice(['reentrancy', 'underflow', 'access control'])}",
            "details": [
                f"Vulnerability: {random.choice(['unchecked call', 'missing require', 'integer overflow'])}",
                f"Fix: Use SafeMath / OpenZeppelin guards",
                f"Lines affected: {random.randint(1, 5)}",
            ],
        },
    }

    result = results.get(model_domain, results["NLP"])
    return result["output"], result["details"], confidence, compute_time, input_hash


def generate_zkml_proof(input_hash, output_hash):
    """Generate zkML proof of computation."""
    time.sleep(random.uniform(0.3, 0.8))
    proof = hashlib.sha256(f"{input_hash}:{output_hash}:{time.time()}".encode()).hexdigest()
    return proof[:64]


# ═══════════════════════════════════════════════════════════
# Miner Node
# ═══════════════════════════════════════════════════════════
class Miner:
    def __init__(self, client, miner_uid, netuid=1):
        self.client = client
        self.uid = miner_uid
        self.netuid = netuid
        self.tasks_completed = 0
        self.proofs_generated = 0
        self.total_earnings = 0.0
        self.running = True
        self.start_time = time.time()

        # Ensure task directory exists
        TASK_DIR.mkdir(exist_ok=True)

    def log(self, emoji, msg, **kwargs):
        ts = datetime.now().strftime("%H:%M:%S")
        extra = " | ".join(f"{k}={v}" for k, v in kwargs.items()) if kwargs else ""
        print(f"  [{ts}] {emoji} {msg}" + (f"  ({extra})" if extra else ""))

    def header(self):
        node = self.client.subnet.get_node(self.netuid, self.uid)
        print()
        print("╔" + "═" * 58 + "╗")
        print("║  ⛏️   ModernTensor MINER Node                             ║")
        print("║  Polkadot Hub Testnet — Decentralized AI Inference        ║")
        print("╚" + "═" * 58 + "╝")
        print(f"  Miner UID:    {self.uid}")
        print(f"  Hotkey:       {node.hotkey}")
        print(f"  Coldkey:      {node.coldkey[:20]}...")
        print(f"  Stake:        {node.total_stake_ether:.2f} MDT")
        print(f"  Trust Score:  {node.trust_float:.2%}")
        print(f"  Subnet:       {self.netuid}")
        print(f"  Status:       {'🟢 ACTIVE' if node.active else '🔴 INACTIVE'}")
        print(f"  Block:        {self.client.block_number}")
        print("─" * 60)

    def poll_for_tasks(self):
        """Poll the shared task queue for pending tasks."""
        pattern = str(TASK_DIR / "task_*.json")
        task_files = sorted(glob.glob(pattern))

        pending = []
        for tf in task_files:
            try:
                with open(tf) as f:
                    task = json.load(f)
                if task.get("status") == "pending":
                    pending.append((tf, task))
            except Exception:
                continue
        return pending

    def process_task(self, task_file, task):
        """Process a task received from a validator."""
        task_id = task["task_id"]
        domain = task["domain"]
        input_data = task["input"]
        validator_uid = task["validator_uid"]

        self.log("📥", f"TASK RECEIVED from Validator UID={validator_uid}",
                 task_id=task_id)
        self.log("🎯", f"Domain: {task['domain_name']}", task=task["task_name"])
        self.log("🧠", f"Input: \"{input_data[:65]}...\"")

        # Run AI inference
        self.log("⚙️", "Running AI model inference...")
        output, details, confidence, compute_time, input_hash = run_inference(domain, input_data)
        self.log("💡", f"Result: {output}", confidence=f"{confidence:.2%}")
        for detail in details:
            self.log("   ", f"  → {detail}")
        self.log("⏱️", f"Compute time: {compute_time:.2f}s")

        # Generate zkML proof
        self.log("🔐", "Generating zkML proof of computation...")
        output_hash = hashlib.sha256(output.encode()).hexdigest()[:16]
        proof = generate_zkml_proof(input_hash, output_hash)
        self.proofs_generated += 1
        self.log("📋", f"Proof: 0x{proof[:32]}...", type="RISC-V zkVM")

        # Write result back to task file
        task["status"] = "completed"
        task["result"] = {
            "miner_uid": self.uid,
            "output": output,
            "details": details,
            "confidence": confidence,
            "compute_time": compute_time,
            "proof": proof,
            "input_hash": input_hash,
            "output_hash": output_hash,
            "timestamp": datetime.now().isoformat(),
        }
        with open(task_file, "w") as f:
            json.dump(task, f, indent=2)

        self.tasks_completed += 1
        self.log("✅", f"Task {task_id} complete — result sent to validator",
                 total=self.tasks_completed)
        return task

    def check_and_claim_rewards(self):
        """Check and claim pending emission rewards."""
        try:
            node = self.client.subnet.get_node(self.netuid, self.uid)
            if node.emission > 0:
                emission = node.emission_ether
                self.log("💰", f"Pending emission: {emission:.6f} MDT — claiming...")
                tx = self.client.subnet.claim_emission(self.netuid, self.uid)
                self.total_earnings += emission
                self.log("🎉", f"Claimed {emission:.6f} MDT!", tx=tx[:16] + "...")
                return emission
        except Exception as e:
            if "No emission" not in str(e):
                self.log("⚠️", f"Claim check: {str(e)[:60]}")
        return 0.0

    def print_status(self):
        """Print miner status summary."""
        try:
            node = self.client.subnet.get_node(self.netuid, self.uid)
            uptime = time.time() - self.start_time
            print(f"\n  ╭── Miner Status (UID={self.uid}) ──────────────────╮")
            print(f"  │  Tasks Completed:  {self.tasks_completed:<26} │")
            print(f"  │  Proofs Generated: {self.proofs_generated:<26} │")
            print(f"  │  Trust Score:      {node.trust_float:<26.4f} │")
            print(f"  │  Pending Emission: {node.emission_ether:<26.6f} │")
            print(f"  │  Total Earnings:   {self.total_earnings:<20.6f}  MDT│")
            print(f"  │  Uptime:           {uptime/60:<20.1f}  min│")
            print(f"  ╰──────────────────────────────────────────────────╯\n")
        except Exception:
            pass

    def run_loop(self, max_rounds=None):
        """Main miner loop — poll for tasks from validators."""
        self.header()
        print(f"\n  🔄 Listening for tasks from validators (polling every {POLL_INTERVAL}s)...")
        print(f"  💡 Start a validator: python demo/validator.py")
        print(f"  ⏹️  Press Ctrl+C to stop\n")

        tasks_done = 0
        idle_count = 0

        while self.running:
            if max_rounds and tasks_done >= max_rounds:
                self.log("🏁", f"Max tasks ({max_rounds}) reached")
                break

            # Poll for pending tasks
            pending = self.poll_for_tasks()

            if not pending:
                idle_count += 1
                if idle_count % 5 == 1:  # Log every 5th idle poll
                    self.log("⏳", "Waiting for tasks from validator...",
                             block=self.client.block_number)
                # Check rewards while idle
                if idle_count % 10 == 0:
                    self.check_and_claim_rewards()
                time.sleep(POLL_INTERVAL)
                continue

            idle_count = 0

            # Process each pending task
            for task_file, task in pending:
                print(f"\n  ─── Task {tasks_done + 1} {'─' * 42}")
                try:
                    self.process_task(task_file, task)
                    tasks_done += 1
                except Exception as e:
                    self.log("❌", f"Task error: {e}")

            # Status every 5 tasks
            if tasks_done % 5 == 0 and tasks_done > 0:
                self.print_status()

        # Final cleanup
        self.check_and_claim_rewards()
        self.print_status()

    def stop(self):
        self.running = False


def main():
    from sdk.polkadot.client import PolkadotClient

    # Load wallets
    with open(WALLET_FILE) as f:
        wallets = json.load(f)

    # Load demo results
    demo_results_path = PROJECT_ROOT / "luxtensor" / "contracts" / "demo-results.json"
    with open(demo_results_path) as f:
        demo = json.load(f)

    miner_key_name = f"miner{MINER_ID}"
    miner_info = demo["nodes"].get(miner_key_name)
    if not miner_info:
        print(f"❌ Miner {MINER_ID} not found in demo-results.json")
        sys.exit(1)

    miner_uid = miner_info["uid"]

    client = PolkadotClient(
        rpc_url=RPC_URL,
        private_key=wallets["miner"]["key"],
        deployment_path=DEPLOYMENT,
    )

    if not client.is_connected:
        print("❌ Cannot connect to Polkadot Hub Testnet")
        sys.exit(1)

    miner = Miner(client, miner_uid=miner_uid, netuid=NETUID)

    def handle_sigint(sig, frame):
        print("\n\n  ⏹️  Shutting down miner gracefully...")
        miner.stop()
        miner.check_and_claim_rewards()
        miner.print_status()
        print("  👋 Miner stopped.\n")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sigint)

    max_rounds = int(os.environ.get("MAX_ROUNDS", "0")) or None
    miner.run_loop(max_rounds=max_rounds)


if __name__ == "__main__":
    main()
