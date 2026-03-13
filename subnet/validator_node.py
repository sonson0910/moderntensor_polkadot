#!/usr/bin/env python3
"""
ModernTensor Validator — Continuous Loop (Bittensor-style)
═══════════════════════════════════════════════════════════════

Chạy vô hạn: tạo task → đánh giá miner → set weights → epoch → rewards.
Sau mỗi epoch: update metagraph, claim rewards, hiện full state.

Mỗi validator chạy trong 1 terminal riêng.
"""

import os
import sys
import time
import json
import signal
import random
import uuid
import glob
from pathlib import Path
from datetime import datetime

SUBNET_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SUBNET_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from subnet.base import (
    CFG, NETUID, TASK_DIR,
    TASK_CATALOG,
    log, show_metagraph, get_client, get_deployer,
)
from web3 import Web3

# ═══════════════════════════════════════════════════════════
# Config
# ═══════════════════════════════════════════════════════════
VALIDATOR_ID   = int(os.environ.get("VALIDATOR_ID", "1"))
POLL_INTERVAL  = float(os.environ.get("POLL_INTERVAL", str(CFG["timing"]["validator_poll_interval"])))
MINER_TIMEOUT  = float(os.environ.get("MINER_TIMEOUT", str(CFG["timing"]["miner_timeout"])))

_key = f"validator{VALIDATOR_ID}"
if _key not in CFG["nodes"]:
    print(f"  ❌ {_key} not found in config.json")
    sys.exit(1)

VAL_UID = CFG["nodes"][_key]["uid"]
HOTKEY  = CFG["nodes"][_key]["hotkey"]


class ContinuousValidator:
    def __init__(self):
        self.client = get_client("validator_coldkey")
        self.deployer = get_deployer()
        self.uid = VAL_UID
        self.running = True
        self.epoch_count = 0
        self.total_earnings = 0.0
        self.start_time = time.time()

    def banner(self):
        """Print startup banner."""
        node = self.client.subnet.get_node(NETUID, self.uid)
        sn = self.client.subnet.get_subnet(NETUID)

        print()
        print("╔" + "═" * 62 + "╗")
        print(f"║  🔷  ModernTensor VALIDATOR {VALIDATOR_ID}                                ║")
        print("║  Polkadot Hub Testnet — Continuous Validation Loop            ║")
        print("╚" + "═" * 62 + "╝")
        print(f"  Validator UID: {self.uid}")
        print(f"  Hotkey:        {HOTKEY}")
        print(f"  Stake:         {node.total_stake_ether:.2f} MDT")
        print(f"  Trust:         {node.trust_float:.2%}")
        print(f"  Subnet:        {sn.name} (netuid={NETUID})")
        print(f"  Nodes:         {sn.node_count} active")
        print(f"  Tempo:         {sn.tempo} block(s)/epoch")
        print(f"  Status:        {'🟢 ACTIVE' if node.active else '🔴 INACTIVE'}")
        print(f"  Block:         {self.client.block_number}")
        print("─" * 64)

    def get_active_miners(self):
        """Get list of active miner UIDs."""
        sn = self.client.subnet.get_subnet(NETUID)
        miners = []
        for uid in range(sn.node_count + 10):
            try:
                node = self.client.subnet.get_node(NETUID, uid)
                if node.active and node.is_miner:
                    miners.append(uid)
            except Exception:
                continue
        return miners

    def create_task(self, task_def, input_data):
        """Create a task in the queue for miners."""
        task_id = str(uuid.uuid4())[:8]
        task = {
            "task_id": task_id,
            "domain": task_def["domain"],
            "domain_name": task_def["domain_name"],
            "task_name": task_def["task_name"],
            "input": input_data,
            "validator_uid": self.uid,
            "created_at": datetime.now().isoformat(),
            "status": "pending",
            "result": None,
        }
        task_file = TASK_DIR / f"task_{task_id}.json"
        with open(task_file, "w") as f:
            json.dump(task, f, indent=2)
        return task_id, str(task_file)

    def wait_for_result(self, task_file, task_id):
        """Wait for a miner to complete the task."""
        start = time.time()
        while time.time() - start < MINER_TIMEOUT:
            try:
                with open(task_file) as f:
                    task = json.load(f)
                if task.get("status") == "completed" and task.get("result"):
                    return task
            except Exception:
                pass
            time.sleep(1.0)
        return None

    def evaluate_result(self, task):
        """Evaluate miner result quality → score 0.0-1.0."""
        result = task["result"]
        confidence = result.get("confidence", 0.5)
        has_proof = bool(result.get("proof"))
        compute_time = result.get("compute_time", 5.0)

        score = 0.0
        score += confidence * 0.50
        score += 0.30 if has_proof else 0
        score += min(0.20, 0.20 * (1.0 / max(compute_time, 0.5)))
        return min(1.0, score)

    def run_validation_round(self, epoch_num, miner_uids):
        """Run one validation round: create task → wait → evaluate → score."""
        task_def = random.choice(TASK_CATALOG)
        input_data = random.choice(task_def["inputs"])

        log("📋", f"Task: {task_def['task_name']}", domain=task_def["domain"])
        log("📝", f"Input: \"{input_data[:70]}{'...' if len(input_data)>70 else ''}\"")

        task_id, task_file = self.create_task(task_def, input_data)
        log("📤", f"Task dispatched → waiting for miner...", task_id=task_id)

        # Wait for result
        completed = self.wait_for_result(task_file, task_id)
        if not completed:
            log("⚠️", "No miner responded — skipping")
            log("💡", "Start miners: python subnet/miner1.py")
            try: os.remove(task_file)
            except: pass
            return {}

        # Evaluate
        result = completed["result"]
        miner_uid = result["miner_uid"]
        log("📬", f"Result from Miner UID={miner_uid}")
        log("🤖", f"Model: {result.get('model_name', '?')}")
        log("💡", f"Output: {result['output']}")
        log("🔐", f"zkML Proof: 0x{result['proof'][:40]}...")

        score = self.evaluate_result(completed)
        log("📊", f"QUALITY SCORE",
            score=f"{score:.4f}",
            confidence=f"{result['confidence']:.2%}",
            time=f"{result['compute_time']:.2f}s",
            proof="✅" if result.get("proof") else "❌")

        # Score all miners
        scores = {}
        for uid in miner_uids:
            if uid == miner_uid:
                scores[uid] = score
            else:
                scores[uid] = max(0.1, score * random.uniform(0.3, 0.7))

        try: os.remove(task_file)
        except: pass
        return scores

    def set_weights_onchain(self, scores):
        """Set consensus weights on-chain."""
        if not scores:
            return False

        log("⚖️", "Setting consensus weights on-chain...")
        uids = list(scores.keys())
        total = sum(scores.values())
        if total == 0:
            return False

        weights = [max(1, int((s / total) * 10000)) for s in scores.values()]

        try:
            tx = self.deployer.subnet.set_weights(
                NETUID, uids, weights, validator_uid=self.uid
            )
            log("✅", "Weights committed!", tx=tx[:16] + "...")
            for uid, w in zip(uids, weights):
                log("📈", f"  Miner UID={uid} → weight={w}")
            return True
        except Exception as e:
            log("⚠️", f"Weight error: {str(e)[:80]}")
            return False

    def run_epoch(self):
        """Trigger epoch — distribute emissions."""
        log("🔄", "Triggering epoch emission distribution...")
        try:
            tx = self.deployer.subnet.run_epoch(NETUID)
            self.epoch_count += 1
            log("🚀", f"═══ EPOCH {self.epoch_count} COMPLETED ═══", tx=tx[:16] + "...")

            # Show emission for each node
            sn = self.client.subnet.get_subnet(NETUID)
            for uid in range(sn.node_count + 10):
                try:
                    node = self.client.subnet.get_node(NETUID, uid)
                    if node.active and node.emission > 0:
                        ntype = "🔷 Val" if node.is_validator else "⛏️ Miner"
                        log("💎", f"  {ntype} UID={uid}: +{node.emission_ether:.6f} MDT")
                except Exception:
                    continue
            return True
        except Exception as e:
            msg = str(e)
            if "Too early" in msg:
                log("⏳", "Not enough blocks yet — will retry next round")
            else:
                log("ℹ️", f"Epoch: {msg[:80]}")
            return False

    def claim_rewards(self):
        """Claim pending emission rewards."""
        try:
            node = self.client.subnet.get_node(NETUID, self.uid)
            if node.emission > 0:
                emission = node.emission_ether
                tx = self.client.subnet.claim_emission(NETUID, self.uid)
                self.total_earnings += emission
                log("💰", f"CLAIMED {emission:.6f} MDT!",
                    tx=tx[:16] + "...", total=f"{self.total_earnings:.6f}")
                return emission
        except Exception as e:
            if "No emission" not in str(e):
                log("ℹ️", f"Claim: {str(e)[:60]}")
        return 0.0

    def show_status(self):
        """Show validator status summary."""
        try:
            node = self.client.subnet.get_node(NETUID, self.uid)
            uptime = (time.time() - self.start_time) / 60

            print(f"\n  ╭── Validator {VALIDATOR_ID} Status (UID={self.uid}) ──────────────────────╮")
            print(f"  │  Epochs Completed:  {self.epoch_count:<30}│")
            print(f"  │  Trust Score:       {node.trust_float:<30.4f}│")
            print(f"  │  Total Earnings:    {self.total_earnings:<25.6f} MDT│")
            print(f"  │  Uptime:            {uptime:<25.1f} min│")
            print(f"  ╰────────────────────────────────────────────────────────────╯")
        except Exception:
            pass

    def run(self):
        """Main continuous validation loop — runs forever like Bittensor."""
        self.banner()
        print(f"\n  🔄 Starting continuous validation (every {POLL_INTERVAL}s)")
        print(f"  💡 Start miners first: python subnet/miner1.py")
        print(f"  ⏹️  Press Ctrl+C to stop\n")

        while self.running:
            # ── Step 1: Find active miners ─────────────────────
            miner_uids = self.get_active_miners()
            if not miner_uids:
                log("⚠️", "No active miners — waiting...")
                time.sleep(POLL_INTERVAL)
                continue

            # ── Step 2: Validation round ───────────────────────
            print(f"\n  ═══ Epoch {self.epoch_count + 1} — Validation Round {'═' * 30}")
            log("👥", f"Active miners: {miner_uids}")

            scores = self.run_validation_round(self.epoch_count + 1, miner_uids)

            # ── Step 3: Set weights on-chain ───────────────────
            if scores:
                self.set_weights_onchain(scores)

            # ── Step 4: Run epoch ──────────────────────────────
            epoch_ok = self.run_epoch()

            # ── Step 5: Claim rewards ──────────────────────────
            if epoch_ok:
                time.sleep(2)  # Wait for state to settle
                self.claim_rewards()

            # ── Step 6: Update metagraph ───────────────────────
            self.show_status()
            show_metagraph(self.client)

            # ── Wait before next epoch ─────────────────────────
            log("⏳", f"Next epoch in {POLL_INTERVAL}s...\n")
            time.sleep(POLL_INTERVAL)

    def stop(self):
        self.running = False
        print(f"\n  ⏹️  Shutting down Validator {VALIDATOR_ID}...")
        self.claim_rewards()
        self.show_status()
        show_metagraph(self.client)
        print(f"  👋 Validator {VALIDATOR_ID} stopped.\n")


def main():
    validator = ContinuousValidator()

    def on_sigint(sig, frame):
        validator.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, on_sigint)
    validator.run()


if __name__ == "__main__":
    main()
