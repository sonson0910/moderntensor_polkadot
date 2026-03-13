#!/usr/bin/env python3
"""
ModernTensor Miner Node — Subnet Demo
═══════════════════════════════════════

Miner nhận task từ Validator, chạy AI inference, tạo zkML proof, trả kết quả.

Usage:
  python subnet/miner_node.py                  # Miner 1 (UID=0)
  MINER_ID=2 python subnet/miner_node.py      # Miner 2 (UID=1)
  MAX_ROUNDS=10 python subnet/miner_node.py   # Chạy 10 rounds rồi dừng
"""

import os
import sys
import time
import json
import random
import hashlib
import signal
import glob
import uuid
from pathlib import Path
from datetime import datetime

# ═══════════════════════════════════════════════════════════
# Path Setup
# ═══════════════════════════════════════════════════════════
SUBNET_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SUBNET_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

CONFIG_FILE = SUBNET_DIR / "config.json"
TASK_DIR = SUBNET_DIR / "task_queue"
TASK_DIR.mkdir(exist_ok=True)

with open(CONFIG_FILE) as f:
    CFG = json.load(f)

RPC_URL = CFG["network"]["rpc_url"]
NETUID = CFG["subnet"]["netuid"]
DEPLOYMENT = str(PROJECT_ROOT / CFG["deployment_file"])
MINER_ID = int(os.environ.get("MINER_ID", "1"))
POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL", str(CFG["timing"]["miner_poll_interval"])))
MAX_ROUNDS = int(os.environ.get("MAX_ROUNDS", "0")) or None

# Resolve miner UID from config
_miner_key = f"miner{MINER_ID}"
if _miner_key not in CFG["nodes"]:
    print(f"  ❌ Miner {MINER_ID} not found in config.json (available: {list(CFG['nodes'].keys())})")
    sys.exit(1)
MINER_UID = CFG["nodes"][_miner_key]["uid"]
MINER_HOTKEY = CFG["nodes"][_miner_key]["hotkey"]

# ═══════════════════════════════════════════════════════════
# AI Inference Engine (Simulated for demo — replace with real models)
# ═══════════════════════════════════════════════════════════
AI_MODELS = {
    "NLP": {
        "name": "ModernBERT-Sentiment-v3",
        "params": "355M",
        "process": lambda inp, conf: {
            "output": f"Sentiment: {'POSITIVE' if conf > 0.85 else 'NEUTRAL'} ({conf:.2f})",
            "details": [
                f"Key phrases: {', '.join(random.sample(['decentralized', 'AI', 'blockchain', 'polkadot', 'inference', 'trustless'], 3))}",
                f"Emotional tone: {'Optimistic' if conf > 0.85 else 'Neutral'}",
                f"Domain tags: [technology, web3, AI]",
            ],
        },
    },
    "Finance": {
        "name": "FinanceGPT-Risk-v2",
        "params": "1.2B",
        "process": lambda inp, conf: {
            "output": f"Risk Score: {random.uniform(3, 8):.1f}/10 ({'HIGH' if conf < 0.85 else 'MODERATE'})",
            "details": [
                f"VaR (95%, 1-day): -${random.randint(2000, 6000):,}",
                f"Diversification: {'FAIR' if conf > 0.85 else 'POOR'} (HHI={random.uniform(0.2, 0.4):.2f})",
                f"Recommendation: {'Hold' if conf > 0.85 else 'Reduce leverage'}",
            ],
        },
    },
    "Code": {
        "name": "CodeAuditLLM-v4",
        "params": "780M",
        "process": lambda inp, conf: {
            "output": f"Severity: {'CRITICAL' if conf < 0.82 else 'MEDIUM'} — {random.choice(['reentrancy', 'underflow', 'access control'])}",
            "details": [
                f"Vulnerability: {random.choice(['unchecked call', 'missing require', 'integer overflow'])}",
                f"Fix: Use SafeMath / OpenZeppelin guards",
                f"Lines affected: {random.randint(1, 5)}",
            ],
        },
    },
}


def run_inference(domain, input_data):
    """Run AI model inference."""
    compute_start = time.time()
    time.sleep(random.uniform(0.8, 2.5))  # Simulate GPU compute

    input_hash = hashlib.sha256(input_data.encode()).hexdigest()[:16]
    confidence = random.uniform(0.78, 0.98)

    model = AI_MODELS.get(domain, AI_MODELS["NLP"])
    result = model["process"](input_data, confidence)
    compute_time = time.time() - compute_start

    return result["output"], result["details"], confidence, compute_time, input_hash, model


def generate_zkml_proof(input_hash, output_hash, model_name):
    """Generate zkML proof of correct AI computation."""
    time.sleep(random.uniform(0.3, 0.8))
    proof_input = f"{input_hash}:{output_hash}:{model_name}:{time.time()}"
    proof = hashlib.sha256(proof_input.encode()).hexdigest()
    return proof[:64]


# ═══════════════════════════════════════════════════════════
# Miner Node
# ═══════════════════════════════════════════════════════════
class MinerNode:
    def __init__(self, client):
        self.client = client
        self.uid = MINER_UID
        self.netuid = NETUID
        self.tasks_completed = 0
        self.proofs_generated = 0
        self.total_earnings = 0.0
        self.running = True
        self.start_time = time.time()

    def log(self, emoji, msg, **kw):
        ts = datetime.now().strftime("%H:%M:%S")
        extra = " | ".join(f"{k}={v}" for k, v in kw.items()) if kw else ""
        print(f"  [{ts}] {emoji} {msg}" + (f"  ({extra})" if extra else ""))

    def banner(self):
        """Print startup banner with on-chain data."""
        try:
            node = self.client.subnet.get_node(self.netuid, self.uid)
            sn = self.client.subnet.get_subnet(self.netuid)
        except Exception as e:
            print(f"\n  ❌ Cannot read on-chain data: {e}")
            sys.exit(1)

        print()
        print("╔" + "═" * 62 + "╗")
        print("║  ⛏️   ModernTensor MINER Node                                 ║")
        print("║  Polkadot Hub Testnet — Decentralized AI Inference             ║")
        print("╚" + "═" * 62 + "╝")
        print(f"  Miner UID:    {self.uid}")
        print(f"  Hotkey:       {node.hotkey}")
        print(f"  Coldkey:      {node.coldkey[:20]}...")
        print(f"  Stake:        {node.total_stake_ether:.2f} MDT")
        print(f"  Trust Score:  {node.trust_float:.2%}")
        print(f"  Subnet:       {sn.name} (netuid={self.netuid})")
        print(f"  Status:       {'🟢 ACTIVE' if node.active else '🔴 INACTIVE'}")
        print(f"  Block:        {self.client.block_number}")
        print("─" * 64)
        print(f"\n  🧠 AI Models loaded:")
        for domain, model in AI_MODELS.items():
            print(f"     • {domain:>8}: {model['name']} ({model['params']})")
        print()

    def poll_tasks(self):
        """Scan task queue for pending tasks."""
        pending = []
        for tf in sorted(glob.glob(str(TASK_DIR / "task_*.json"))):
            try:
                with open(tf) as f:
                    task = json.load(f)
                if task.get("status") == "pending":
                    pending.append((tf, task))
            except Exception:
                continue
        return pending

    def process_task(self, task_file, task):
        """Process an AI inference task from a validator."""
        task_id = task["task_id"]
        domain = task["domain"]
        input_data = task["input"]
        val_uid = task["validator_uid"]

        self.log("📥", f"TASK RECEIVED from Validator UID={val_uid}", task_id=task_id)
        self.log("🎯", f"Domain: {task['domain_name']}", task=task["task_name"])
        self.log("📝", f"Input: \"{input_data[:70]}{'...' if len(input_data)>70 else ''}\"")

        # Step 1: Run AI inference
        self.log("⚙️", "Running AI model inference...")
        output, details, confidence, compute_time, input_hash, model = run_inference(domain, input_data)
        self.log("🤖", f"Model: {model['name']} ({model['params']})")
        self.log("💡", f"Result: {output}", confidence=f"{confidence:.2%}")
        for d in details:
            self.log("   ", f"  → {d}")
        self.log("⏱️", f"Compute time: {compute_time:.2f}s")

        # Step 2: Generate zkML proof
        self.log("🔐", "Generating zkML proof of computation...")
        output_hash = hashlib.sha256(output.encode()).hexdigest()[:16]
        proof = generate_zkml_proof(input_hash, output_hash, model["name"])
        self.proofs_generated += 1
        self.log("📋", f"zkML Proof: 0x{proof[:40]}...", verifier="RISC-V zkVM")

        # Step 3: Write result back
        task["status"] = "completed"
        task["result"] = {
            "miner_uid": self.uid,
            "model_name": model["name"],
            "model_params": model["params"],
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
        self.log("✅", f"Task {task_id} COMPLETE — result returned to validator",
                 total_done=self.tasks_completed)

    def check_rewards(self):
        """Check and claim pending emission rewards."""
        try:
            node = self.client.subnet.get_node(self.netuid, self.uid)
            if node.emission > 0:
                emission = node.emission_ether
                self.log("💰", f"Pending emission: {emission:.6f} MDT — claiming...")
                tx = self.client.subnet.claim_emission(self.netuid, self.uid)
                self.total_earnings += emission
                self.log("🎉", f"CLAIMED {emission:.6f} MDT!", tx=tx[:16] + "...")
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
            print(f"\n  ╭── Miner Status (UID={self.uid}) ─────────────────────────────╮")
            print(f"  │  Tasks Completed:   {self.tasks_completed:<30} │")
            print(f"  │  Proofs Generated:  {self.proofs_generated:<30} │")
            print(f"  │  Trust Score:       {node.trust_float:<30.4f} │")
            print(f"  │  Rank:              {node.rank_float:<30.6f} │")
            print(f"  │  Pending Emission:  {node.emission_ether:<30.6f} │")
            print(f"  │  Total Earnings:    {self.total_earnings:<24.6f}  MDT│")
            print(f"  │  Uptime:            {uptime/60:<24.1f}  min│")
            print(f"  ╰──────────────────────────────────────────────────────────────╯\n")
        except Exception:
            pass

    def run(self):
        """Main miner loop."""
        self.banner()
        print(f"  🔄 Listening for tasks from validators (polling every {POLL_INTERVAL}s)...")
        print(f"  💡 Start a validator: python subnet/validator_node.py")
        print(f"  ⏹️  Press Ctrl+C to stop\n")

        tasks_done = 0
        idle_count = 0

        while self.running:
            if MAX_ROUNDS and tasks_done >= MAX_ROUNDS:
                self.log("🏁", f"Max tasks ({MAX_ROUNDS}) reached — stopping")
                break

            pending = self.poll_tasks()

            if not pending:
                idle_count += 1
                if idle_count % 5 == 1:
                    self.log("⏳", "Waiting for tasks from validator...",
                             block=self.client.block_number)
                if idle_count % 10 == 0:
                    self.check_rewards()
                time.sleep(POLL_INTERVAL)
                continue

            idle_count = 0
            for task_file, task in pending:
                print(f"\n  ─── Task {tasks_done + 1} {'─' * 48}")
                try:
                    self.process_task(task_file, task)
                    tasks_done += 1
                except Exception as e:
                    self.log("❌", f"Task error: {e}")

            if tasks_done % 3 == 0 and tasks_done > 0:
                self.print_status()

        # Final
        self.check_rewards()
        self.print_status()

    def stop(self):
        self.running = False


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════
def main():
    from sdk.polkadot.client import PolkadotClient

    client = PolkadotClient(
        rpc_url=RPC_URL,
        private_key=CFG["wallets"]["miner_coldkey"]["key"],
        deployment_path=DEPLOYMENT,
    )

    if not client.is_connected:
        print("  ❌ Cannot connect to Polkadot Hub Testnet")
        sys.exit(1)

    miner = MinerNode(client)

    def on_sigint(sig, frame):
        print("\n\n  ⏹️  Shutting down miner gracefully...")
        miner.stop()
        miner.check_rewards()
        miner.print_status()
        print("  👋 Miner stopped.\n")
        sys.exit(0)

    signal.signal(signal.SIGINT, on_sigint)
    miner.run()


if __name__ == "__main__":
    main()
