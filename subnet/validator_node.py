#!/usr/bin/env python3
"""
ModernTensor Validator Node — Subnet Demo
═══════════════════════════════════════════

Validator tạo task AI → gửi cho Miner → đánh giá → set weights → epoch → rewards.

Usage:
  python subnet/validator_node.py                     # Validator 1 (UID=2)
  VALIDATOR_ID=2 python subnet/validator_node.py      # Validator 2 (UID=3)
  MAX_ROUNDS=5 python subnet/validator_node.py        # Chạy 5 rounds
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
VALIDATOR_ID = int(os.environ.get("VALIDATOR_ID", "1"))
POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL", str(CFG["timing"]["validator_poll_interval"])))
MINER_TIMEOUT = float(os.environ.get("MINER_TIMEOUT", str(CFG["timing"]["miner_timeout"])))
MAX_ROUNDS = int(os.environ.get("MAX_ROUNDS", "0")) or None

# Resolve validator UID
_val_key = f"validator{VALIDATOR_ID}"
if _val_key not in CFG["nodes"]:
    print(f"  ❌ Validator {VALIDATOR_ID} not found (available: {list(CFG['nodes'].keys())})")
    sys.exit(1)
VAL_UID = CFG["nodes"][_val_key]["uid"]

from web3 import Web3

# ═══════════════════════════════════════════════════════════
# Task Catalog — Tasks để gửi cho Miners
# ═══════════════════════════════════════════════════════════
TASK_CATALOG = [
    {
        "domain": "NLP",
        "domain_name": "Natural Language Processing",
        "task_name": "Sentiment Analysis",
        "inputs": [
            "Polkadot's parachain architecture enables unprecedented interoperability between blockchains, making cross-chain AI possible.",
            "ModernTensor brings decentralized AI inference to the Polkadot ecosystem through verifiable computation and zkML proofs.",
            "Web3 AI solutions are transforming how we approach data privacy, model ownership, and decentralized intelligence.",
            "The convergence of blockchain technology and artificial intelligence creates new paradigms for trustless computation.",
            "Decentralized GPU networks will democratize AI access, removing barriers for developers in emerging markets.",
        ],
    },
    {
        "domain": "Finance",
        "domain_name": "Financial Analysis",
        "task_name": "Risk Assessment",
        "inputs": [
            "Portfolio: ETH 40%, DOT 30%, MDT 20%, USDC 10% — leverage 1.5x, duration 90 days. Assess risk profile.",
            "DeFi lending position: $50k AAVE at 5.2% APY, health factor 1.8, utilization 65%. Evaluate safety margin.",
            "Cross-chain liquidity farming: 3 positions across Polkadot parachains, total TVL $120k. Calculate impermanent loss risk.",
        ],
    },
    {
        "domain": "Code",
        "domain_name": "Smart Contract Security",
        "task_name": "Smart Contract Audit",
        "inputs": [
            "function transfer(address to, uint256 amount) external { balances[msg.sender] -= amount; balances[to] += amount; }",
            "function withdraw() external { (bool ok,) = msg.sender.call{value: balances[msg.sender]}(''); balances[msg.sender] = 0; }",
            "function approve(address spender, uint256 amount) public { allowance[msg.sender][spender] = amount; }",
        ],
    },
]


# ═══════════════════════════════════════════════════════════
# Validator Node
# ═══════════════════════════════════════════════════════════
class ValidatorNode:
    def __init__(self, client, deployer_client):
        self.client = client
        self.deployer = deployer_client
        self.uid = VAL_UID
        self.netuid = NETUID
        self.rounds_completed = 0
        self.total_earnings = 0.0
        self.start_time = time.time()
        self.running = True

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
        print("║  🔷  ModernTensor VALIDATOR Node                              ║")
        print("║  Polkadot Hub Testnet — Enhanced Yuma Consensus Engine        ║")
        print("╚" + "═" * 62 + "╝")
        print(f"  Validator UID: {self.uid}")
        print(f"  Hotkey:        {node.hotkey}")
        print(f"  Coldkey:       {node.coldkey[:20]}...")
        print(f"  Stake:         {node.total_stake_ether:.2f} MDT")
        print(f"  Trust Score:   {node.trust_float:.2%}")
        print(f"  Subnet:        {sn.name} (netuid={self.netuid})")
        print(f"  Nodes:         {sn.node_count} active ({sn.max_nodes} max)")
        print(f"  Tempo:         {sn.tempo} block(s)/epoch")
        print(f"  Status:        {'🟢 ACTIVE' if node.active else '🔴 INACTIVE'}")
        print(f"  Block:         {self.client.block_number}")
        print("─" * 64)

    def get_miner_uids(self):
        """Get all active miner UIDs in subnet."""
        sn = self.client.subnet.get_subnet(self.netuid)
        miners = []
        for uid in range(sn.node_count + 5):
            try:
                node = self.client.subnet.get_node(self.netuid, uid)
                if node.active and node.is_miner:
                    miners.append(uid)
            except Exception:
                continue
        return miners

    def create_task(self, task_def, input_data):
        """Create a task and put it in the queue for miners."""
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
        dots = 0
        while time.time() - start < MINER_TIMEOUT:
            try:
                with open(task_file) as f:
                    task = json.load(f)
                if task.get("status") == "completed" and task.get("result"):
                    return task
            except Exception:
                pass
            dots += 1
            if dots % 3 == 0:
                self.log("⏳", f"Waiting for miner... ({time.time()-start:.0f}s)")
            time.sleep(1.0)
        self.log("⚠️", f"Task {task_id} TIMEOUT after {MINER_TIMEOUT}s — no miner responded")
        return None

    def evaluate_result(self, task):
        """Evaluate miner result quality."""
        result = task["result"]
        confidence = result.get("confidence", 0.5)
        has_proof = bool(result.get("proof"))
        compute_time = result.get("compute_time", 0)

        quality = 0.0
        quality += confidence * 0.50            # 50% model confidence
        quality += 0.30 if has_proof else 0     # 30% proof existence
        quality += min(0.20, 0.20 * (1.0 / max(compute_time, 0.5)))  # 20% speed
        return min(1.0, quality)

    def run_validation_round(self, round_num, miner_uids):
        """Run one complete validation round."""
        print(f"\n  ═══ Validation Round {round_num} {'═' * 40}")
        self.log("👥", f"Active miners: {miner_uids}")

        # Step 1: Create and dispatch task
        task_def = random.choice(TASK_CATALOG)
        input_data = random.choice(task_def["inputs"])

        self.log("📋", f"Task: {task_def['task_name']}", domain=task_def["domain"])
        self.log("📝", f"Input: \"{input_data[:70]}{'...' if len(input_data)>70 else ''}\"")

        task_id, task_file = self.create_task(task_def, input_data)
        self.log("📤", "Task dispatched to queue → waiting for miner...", task_id=task_id)

        # Step 2: Wait for miner response
        completed = self.wait_for_result(task_file, task_id)
        if not completed:
            self.log("❌", "No miner responded — skipping round")
            self.log("💡", "Start a miner: python subnet/miner_node.py")
            try:
                os.remove(task_file)
            except Exception:
                pass
            return {}

        # Step 3: Evaluate result
        result = completed["result"]
        miner_uid = result["miner_uid"]
        self.log("📬", f"Result from Miner UID={miner_uid}")
        self.log("🤖", f"Model: {result.get('model_name', 'Unknown')}")
        self.log("💡", f"Output: {result['output']}")
        self.log("🔐", f"zkML Proof: 0x{result['proof'][:40]}...")

        score = self.evaluate_result(completed)
        self.log("📊", f"QUALITY EVALUATION",
                 score=f"{score:.4f}",
                 confidence=f"{result['confidence']:.2%}",
                 time=f"{result['compute_time']:.2f}s",
                 proof="✅" if result.get("proof") else "❌")

        # Score all miners (responder gets full score, others estimated)
        scores = {}
        for uid in miner_uids:
            if uid == miner_uid:
                scores[uid] = score
            else:
                scores[uid] = max(0.1, score * random.uniform(0.3, 0.7))
                self.log("📊", f"  Miner UID={uid}", score=f"{scores[uid]:.4f}",
                         note="estimated")

        # Clean up
        try:
            os.remove(task_file)
        except Exception:
            pass

        return scores

    def set_weights(self, scores):
        """Set consensus weights on-chain."""
        if not scores:
            return

        self.log("⚖️", "Setting consensus weights on-chain...")
        uids = list(scores.keys())
        total = sum(scores.values())
        if total == 0:
            return

        weights = [max(1, int((s / total) * 10000)) for s in scores.values()]

        try:
            tx = self.deployer.subnet.set_weights(
                self.netuid, uids, weights, validator_uid=self.uid
            )
            self.log("✅", "Weights committed on-chain!", tx=tx[:16] + "...")
            for uid, w in zip(uids, weights):
                self.log("📈", f"  Miner UID={uid} → weight={w}")
        except Exception as e:
            self.log("⚠️", f"Weight error: {str(e)[:80]}")

    def try_epoch(self):
        """Trigger epoch emission distribution."""
        self.log("🔄", "Triggering epoch emission distribution...")
        try:
            tx = self.deployer.subnet.run_epoch(self.netuid)
            self.log("🚀", "EPOCH COMPLETED — rewards distributed!", tx=tx[:16] + "...")
            self.rounds_completed += 1

            # Show per-node emission
            sn = self.client.subnet.get_subnet(self.netuid)
            for uid in range(sn.node_count + 5):
                try:
                    node = self.client.subnet.get_node(self.netuid, uid)
                    if node.active and node.emission > 0:
                        ntype = "🔷 Validator" if node.is_validator else "⛏️ Miner"
                        self.log("💎", f"  {ntype} UID={uid}: +{node.emission_ether:.6f} MDT")
                except Exception:
                    continue
            return True
        except Exception as e:
            msg = str(e)
            if "Too early" in msg:
                self.log("⏳", "Not enough blocks for epoch yet — will retry")
            else:
                self.log("ℹ️", f"Epoch: {msg[:80]}")
            return False

    def claim_rewards(self):
        """Claim pending emission rewards."""
        try:
            node = self.client.subnet.get_node(self.netuid, self.uid)
            if node.emission > 0:
                emission = node.emission_ether
                tx = self.client.subnet.claim_emission(self.netuid, self.uid)
                self.total_earnings += emission
                self.log("💰", f"CLAIMED {emission:.6f} MDT!", tx=tx[:16] + "...")
                return emission
        except Exception as e:
            if "No emission" not in str(e):
                self.log("ℹ️", f"Claim: {str(e)[:60]}")
        return 0.0

    def show_metagraph(self):
        """Display the full subnet metagraph."""
        try:
            meta = self.client.subnet.get_metagraph(self.netuid)
            sn = self.client.subnet.get_subnet(self.netuid)

            print(f"\n  ╭── Metagraph: {sn.name} (netuid={self.netuid}) ───────────────────────────╮")
            print(f"  │ {'UID':<5} {'Type':<11} {'Stake':<12} {'Trust':<10} {'Rank':<10} {'Emission':<14} │")
            print(f"  │ {'─'*5} {'─'*11} {'─'*12} {'─'*10} {'─'*10} {'─'*14} │")

            for node in meta.nodes:
                if not node.active:
                    continue
                ntype = "VALIDATOR" if node.is_validator else "MINER"
                emoji = "🔷" if node.is_validator else "⛏️"
                print(
                    f"  │ {emoji}{node.uid:<4} {ntype:<11} "
                    f"{node.total_stake_ether:<12.2f} "
                    f"{node.trust_float:<10.4f} "
                    f"{node.rank_float:<10.6f} "
                    f"{node.emission_ether:<14.6f} │"
                )

            total_stake_ether = float(Web3.from_wei(meta.total_stake, "ether"))
            print(f"  │{'─'*72}│")
            print(
                f"  │ Total Stake: {total_stake_ether:.2f} MDT | "
                f"Miners: {len(meta.miners)} | Validators: {len(meta.validators)}"
                f"{' ' * (72 - 45 - len(str(int(total_stake_ether))) - len(str(len(meta.miners))) - len(str(len(meta.validators))))}│"
            )
            print(f"  ╰{'─'*72}╯\n")
        except Exception as e:
            self.log("⚠️", f"Metagraph error: {str(e)[:60]}")

    def run(self):
        """Main validator loop."""
        self.banner()
        print(f"\n  🔄 Starting validator (dispatching tasks every {POLL_INTERVAL}s)")
        print(f"  💡 Start miners first: python subnet/miner_node.py")
        print(f"  ⏹️  Press Ctrl+C to stop\n")

        round_num = 0
        while self.running:
            round_num += 1
            if MAX_ROUNDS and round_num > MAX_ROUNDS:
                self.log("🏁", f"Max rounds ({MAX_ROUNDS}) reached — stopping")
                break

            # Step 1: Find miners
            miner_uids = self.get_miner_uids()
            if not miner_uids:
                self.log("⚠️", "No active miners found — waiting...")
                time.sleep(POLL_INTERVAL)
                continue

            # Step 2: Validate (create task → wait → evaluate)
            scores = self.run_validation_round(round_num, miner_uids)

            # Step 3: Set weights on-chain
            if scores:
                self.set_weights(scores)

            # Step 4: Run epoch
            self.try_epoch()

            # Step 5: Claim rewards
            self.claim_rewards()

            # Step 6: Show metagraph every 2 rounds
            if round_num % 2 == 0:
                self.show_metagraph()

            time.sleep(POLL_INTERVAL)

        # Final
        self.show_metagraph()

    def stop(self):
        self.running = False


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════
def main():
    from sdk.polkadot.client import PolkadotClient

    val_client = PolkadotClient(
        rpc_url=RPC_URL,
        private_key=CFG["wallets"]["validator_coldkey"]["key"],
        deployment_path=DEPLOYMENT,
    )
    deployer_client = PolkadotClient(
        rpc_url=RPC_URL,
        private_key=CFG["wallets"]["deployer"]["key"],
        deployment_path=DEPLOYMENT,
    )

    if not val_client.is_connected:
        print("  ❌ Cannot connect to Polkadot Hub Testnet")
        sys.exit(1)

    validator = ValidatorNode(val_client, deployer_client)

    def on_sigint(sig, frame):
        print("\n\n  ⏹️  Shutting down validator gracefully...")
        validator.stop()
        validator.claim_rewards()
        validator.show_metagraph()
        print("  👋 Validator stopped.\n")
        sys.exit(0)

    signal.signal(signal.SIGINT, on_sigint)
    validator.run()


if __name__ == "__main__":
    main()
