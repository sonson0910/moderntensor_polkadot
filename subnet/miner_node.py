#!/usr/bin/env python3
"""
ModernTensor Miner — Continuous Loop (Bittensor-style)
══════════════════════════════════════════════════════════

Chạy vô hạn: nhận task → AI inference → zkML proof → trả kết quả.
Sau mỗi epoch: claim rewards + update metagraph.

Mỗi miner chạy trong 1 terminal riêng.
"""

import os
import sys
import time
import json
import signal
import glob
from pathlib import Path
from datetime import datetime

SUBNET_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SUBNET_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from subnet.base import (
    CFG, NETUID, TASK_DIR,
    AI_MODELS, generate_zkml_proof,
    log, show_metagraph, get_client, get_deployer,
)

# ═══════════════════════════════════════════════════════════
# Config — Override via args or env
# ═══════════════════════════════════════════════════════════
MINER_ID      = int(os.environ.get("MINER_ID", "1"))
POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL", str(CFG["timing"]["miner_poll_interval"])))

_key = f"miner{MINER_ID}"
if _key not in CFG["nodes"]:
    print(f"  ❌ {_key} not found in config.json")
    sys.exit(1)

MINER_UID = CFG["nodes"][_key]["uid"]
HOTKEY    = CFG["nodes"][_key]["hotkey"]


class ContinuousMiner:
    def __init__(self):
        self.client = get_client("miner_coldkey")
        self.deployer = get_deployer()
        self.uid = MINER_UID
        self.running = True
        self.tasks_done = 0
        self.proofs_generated = 0
        self.total_earnings = 0.0
        self.start_time = time.time()
        self.current_epoch = 0

    def banner(self):
        """Print startup banner with on-chain data."""
        node = self.client.subnet.get_node(NETUID, self.uid)
        sn = self.client.subnet.get_subnet(NETUID)

        print()
        print("╔" + "═" * 62 + "╗")
        print(f"║  ⛏️   ModernTensor MINER {MINER_ID}                                   ║")
        print("║  Polkadot Hub Testnet — Continuous Mining Loop                ║")
        print("╚" + "═" * 62 + "╝")
        print(f"  Miner UID:    {self.uid}")
        print(f"  Hotkey:       {HOTKEY}")
        print(f"  Stake:        {node.total_stake_ether:.2f} MDT")
        print(f"  Trust:        {node.trust_float:.2%}")
        print(f"  Subnet:       {sn.name} (netuid={NETUID})")
        print(f"  Status:       {'🟢 ACTIVE' if node.active else '🔴 INACTIVE'}")
        print(f"  Block:        {self.client.block_number}")
        print("─" * 64)
        print()
        print("  🧠 AI Models loaded:")
        for domain, model in AI_MODELS.items():
            print(f"     • {domain:>8}: {model['name']} ({model['params']})")
        print()

    def poll_task(self):
        """Check task queue for pending tasks. Return (task_data, filepath) or None."""
        for task_file in sorted(glob.glob(str(TASK_DIR / "task_*.json"))):
            try:
                with open(task_file) as f:
                    task = json.load(f)
                if task.get("status") == "pending":
                    return task, task_file
            except Exception:
                continue
        return None, None

    def process_task(self, task, task_file):
        """Run AI inference on a task and return result."""
        domain = task["domain"]
        model = AI_MODELS.get(domain, AI_MODELS["NLP"])
        self.tasks_done += 1

        print(f"\n  ─── Task {self.tasks_done} ────────────────────────────────────────")
        log("📥", f"TASK RECEIVED from Validator UID={task['validator_uid']}", task_id=task["task_id"])
        log("🎯", f"Domain: {model['name']}", task=task["task_name"])
        log("📝", f"Input: \"{task['input'][:70]}{'...' if len(task['input'])>70 else ''}\"")
        log("⚙️", "Running AI model inference...")

        # Simulate compute time
        compute_time = 0.5 + random.uniform(0.3, 2.0)
        time.sleep(min(compute_time, 1.0))

        # Run model
        result = model["run"](task["input"])
        log("🤖", f"Model: {model['name']} ({model['params']})")
        log("💡", f"Result: {result['output']}", confidence=f"{result['confidence']:.2%}")

        if "details" in result:
            for k, v in result["details"].items():
                log("", f"      → {k}: {v}")
        log("⏱️", f"Compute time: {compute_time:.2f}s")

        # Generate zkML proof
        log("🔐", "Generating zkML proof of computation...")
        proof = generate_zkml_proof(model["name"], task["input"], result["output"])
        self.proofs_generated += 1
        log("📋", f"zkML Proof: 0x{proof[:40]}...", verifier="RISC-V zkVM")

        # Write result back to task file
        import random as _rand
        task["status"] = "completed"
        task["result"] = {
            "miner_uid": self.uid,
            "model_name": model["name"],
            "output": result["output"],
            "confidence": result["confidence"],
            "compute_time": compute_time,
            "proof": proof,
            "details": result.get("details", {}),
            "timestamp": datetime.now().isoformat(),
        }
        with open(task_file, "w") as f:
            json.dump(task, f, indent=2)

        log("✅", f"Task {task['task_id']} COMPLETE — result returned to validator", total_done=self.tasks_done)

    def try_claim_rewards(self):
        """Check and claim pending emission rewards."""
        try:
            node = self.client.subnet.get_node(NETUID, self.uid)
            if node.emission > 0:
                emission = node.emission_ether
                tx = self.client.subnet.claim_emission(NETUID, self.uid)
                self.total_earnings += emission
                log("💰", f"CLAIMED {emission:.6f} MDT!", tx=tx[:16] + "...", total=f"{self.total_earnings:.6f}")
                return emission
        except Exception as e:
            if "No emission" not in str(e):
                log("ℹ️", f"Claim: {str(e)[:60]}")
        return 0.0

    def show_status(self):
        """Show current miner status summary."""
        try:
            node = self.client.subnet.get_node(NETUID, self.uid)
            uptime = (time.time() - self.start_time) / 60

            print(f"\n  ╭── Miner {MINER_ID} Status (UID={self.uid}) ─────────────────────────╮")
            print(f"  │  Tasks Completed:   {self.tasks_done:<30}│")
            print(f"  │  Proofs Generated:  {self.proofs_generated:<30}│")
            print(f"  │  Trust Score:       {node.trust_float:<30.4f}│")
            print(f"  │  Rank:              {node.rank_float:<30.6f}│")
            print(f"  │  Pending Emission:  {node.emission_ether:<30.6f}│")
            print(f"  │  Total Earnings:    {self.total_earnings:<25.6f} MDT│")
            print(f"  │  Uptime:            {uptime:<25.1f} min│")
            print(f"  ╰────────────────────────────────────────────────────────────╯")
        except Exception:
            pass

    def run(self):
        """Main continuous mining loop — runs forever like Bittensor."""
        self.banner()
        print(f"  🔄 Listening for tasks (polling every {POLL_INTERVAL}s)...")
        print(f"  💡 Start validators: python subnet/validator1.py")
        print(f"  ⏹️  Press Ctrl+C to stop\n")

        check_counter = 0
        while self.running:
            # Poll for tasks
            task, task_file = self.poll_task()

            if task:
                self.process_task(task, task_file)
            else:
                check_counter += 1
                if check_counter % 5 == 0:  # Every 5 polls
                    log("⏳", f"Waiting for tasks...", block=self.client.block_number)

            # Periodically claim rewards & show metagraph
            if check_counter % 10 == 0 and check_counter > 0:
                self.try_claim_rewards()

            if check_counter % 20 == 0 and check_counter > 0:
                self.show_status()
                show_metagraph(self.client)

            time.sleep(POLL_INTERVAL)

    def stop(self):
        self.running = False
        print(f"\n  ⏹️  Shutting down Miner {MINER_ID} (UID={self.uid})...")
        self.try_claim_rewards()
        self.show_status()
        show_metagraph(self.client)
        print(f"  👋 Miner {MINER_ID} stopped.\n")


def main():
    import random
    miner = ContinuousMiner()

    def on_sigint(sig, frame):
        miner.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, on_sigint)
    miner.run()


if __name__ == "__main__":
    main()
