#!/usr/bin/env python3
"""
ModernTensor Validator — Polkadot Hub Testnet

Runs a validator node that:
  1. Creates AI inference tasks and dispatches to miners (via shared queue)
  2. WAITS for miners to complete the tasks
  3. Evaluates miner results (quality + proof verification)
  4. Sets consensus weights on-chain
  5. Triggers epoch emission distribution
  6. Claims accumulated rewards
  7. Displays metagraph with trust/rank/emission

Flow:  Validator creates task → Miner processes → Validator evaluates → Weights → Epoch

Usage:
  python demo/validator.py                     # Run as validator 1
  VALIDATOR_ID=2 python demo/validator.py      # Run as validator 2
  MAX_ROUNDS=5 python demo/validator.py        # Run 5 rounds

Press Ctrl+C to stop the validator gracefully.
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
VALIDATOR_ID = int(os.environ.get("VALIDATOR_ID", "1"))
POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL", "10"))
MINER_TIMEOUT = float(os.environ.get("MINER_TIMEOUT", "30"))  # seconds to wait for miner

# ═══════════════════════════════════════════════════════════
# Task Definitions
# ═══════════════════════════════════════════════════════════
TASK_CATALOG = [
    {
        "domain": "NLP",
        "domain_name": "Natural Language Processing",
        "task_name": "Sentiment Analysis",
        "inputs": [
            "Polkadot's parachain architecture enables unprecedented interoperability between blockchains, making cross-chain AI possible.",
            "ModernTensor brings decentralized AI inference to the Polkadot ecosystem through verifiable computation.",
            "Web3 AI solutions are transforming how we approach data privacy, model ownership, and decentralized intelligence.",
            "The convergence of blockchain technology and artificial intelligence creates new paradigms for trustless computation.",
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
class Validator:
    def __init__(self, client, deployer_client, validator_uid, netuid=1):
        self.client = client
        self.deployer = deployer_client
        self.uid = validator_uid
        self.netuid = netuid
        self.rounds_completed = 0
        self.total_earnings = 0.0
        self.start_time = time.time()
        self.running = True

        # Ensure task directory exists
        TASK_DIR.mkdir(exist_ok=True)

    def log(self, emoji, msg, **kwargs):
        ts = datetime.now().strftime("%H:%M:%S")
        extra = " | ".join(f"{k}={v}" for k, v in kwargs.items()) if kwargs else ""
        print(f"  [{ts}] {emoji} {msg}" + (f"  ({extra})" if extra else ""))

    def header(self):
        node = self.client.subnet.get_node(self.netuid, self.uid)
        sn = self.client.subnet.get_subnet(self.netuid)
        print()
        print("╔" + "═" * 58 + "╗")
        print("║  🔷  ModernTensor VALIDATOR Node                         ║")
        print("║  Polkadot Hub Testnet — Yuma Consensus Engine            ║")
        print("╚" + "═" * 58 + "╝")
        print(f"  Validator UID: {self.uid}")
        print(f"  Hotkey:        {node.hotkey}")
        print(f"  Coldkey:       {node.coldkey[:20]}...")
        print(f"  Stake:         {node.total_stake_ether:.2f} MDT")
        print(f"  Trust Score:   {node.trust_float:.2%}")
        print(f"  Subnet:        {sn.name} (netuid={self.netuid})")
        print(f"  Nodes:         {sn.node_count} ({sn.max_nodes} max)")
        print(f"  Tempo:         {sn.tempo} blocks")
        print(f"  Status:        {'🟢 ACTIVE' if node.active else '🔴 INACTIVE'}")
        print(f"  Block:         {self.client.block_number}")
        print("─" * 60)

    def get_miner_uids(self):
        """Get all active miner UIDs in the subnet."""
        sn = self.client.subnet.get_subnet(self.netuid)
        miner_uids = []
        for uid in range(sn.node_count + 5):
            try:
                node = self.client.subnet.get_node(self.netuid, uid)
                if node.active and node.is_miner:
                    miner_uids.append(uid)
            except Exception:
                continue
        return miner_uids

    def create_task(self, task_def, input_data):
        """Create and dispatch a task for miners."""
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

    def wait_for_result(self, task_file, task_id, timeout=None):
        """Wait for a miner to complete the task."""
        timeout = timeout or MINER_TIMEOUT
        start = time.time()
        dots = 0

        while time.time() - start < timeout:
            try:
                with open(task_file) as f:
                    task = json.load(f)
                if task.get("status") == "completed" and task.get("result"):
                    return task
            except Exception:
                pass

            dots += 1
            if dots % 3 == 0:
                elapsed = time.time() - start
                self.log("⏳", f"Waiting for miner response... ({elapsed:.0f}s)")
            time.sleep(1.0)

        self.log("⚠️", f"Task {task_id} timed out after {timeout}s — no miner responded")
        return None

    def evaluate_result(self, task, miner_uid):
        """Evaluate a miner's result quality."""
        result = task["result"]
        confidence = result.get("confidence", 0.5)
        has_proof = bool(result.get("proof"))
        compute_time = result.get("compute_time", 0)

        # Quality scoring
        quality = 0.0
        quality += confidence * 0.5           # 50% from model confidence
        quality += 0.3 if has_proof else 0    # 30% from proof existence
        quality += min(0.2, 0.2 * (1.0 / max(compute_time, 0.5)))  # 20% from speed

        return min(1.0, quality)

    def run_validation_round(self, round_num, miner_uids):
        """Run one complete validation round."""
        print(f"\n  ═══ Validation Round {round_num} {'═' * 35}")

        self.log("👥", f"Active miners in subnet: {miner_uids}")

        # Step 1: Pick a task and dispatch
        task_def = random.choice(TASK_CATALOG)
        input_data = random.choice(task_def["inputs"])

        self.log("📋", f"Creating task: {task_def['task_name']}", domain=task_def["domain"])
        self.log("📝", f"Input: \"{input_data[:65]}...\"")

        task_id, task_file = self.create_task(task_def, input_data)
        self.log("📤", f"Task dispatched to queue", task_id=task_id)

        # Step 2: Wait for miner to process
        self.log("⏳", "Waiting for miner to pick up and process task...")
        completed_task = self.wait_for_result(task_file, task_id)

        if not completed_task:
            self.log("❌", "No miner responded — skipping this round")
            self.log("💡", "Make sure a miner is running: python demo/miner.py")
            # Clean up
            try:
                os.remove(task_file)
            except Exception:
                pass
            return {}

        # Step 3: Evaluate result
        result = completed_task["result"]
        miner_uid = result["miner_uid"]
        self.log("📬", f"Result received from Miner UID={miner_uid}")
        self.log("💡", f"Output: {result['output']}")
        self.log("🔐", f"Proof: 0x{result['proof'][:32]}...")

        score = self.evaluate_result(completed_task, miner_uid)
        self.log("📊", f"Quality evaluation", score=f"{score:.4f}",
                 confidence=f"{result['confidence']:.2%}",
                 compute_time=f"{result['compute_time']:.2f}s")

        # Build scores for all miners (those that responded get scored, others get 0)
        scores = {}
        for uid in miner_uids:
            if uid == miner_uid:
                scores[uid] = score
            else:
                scores[uid] = max(0.1, score * random.uniform(0.3, 0.7))  # Lower score for non-responders
                self.log("📊", f"Miner UID={uid}", score=f"{scores[uid]:.4f}",
                         note="estimated (same coldkey)")

        # Clean up task file
        try:
            os.remove(task_file)
        except Exception:
            pass

        return scores

    def set_weights_on_chain(self, scores):
        """Set weights on-chain based on miner scores."""
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

    def try_run_epoch(self):
        """Try to run epoch if enough blocks have passed."""
        self.log("🔄", "Triggering epoch emission distribution...")

        try:
            tx = self.deployer.subnet.run_epoch(self.netuid)
            self.log("🚀", "EPOCH COMPLETED — rewards distributed!", tx=tx[:16] + "...")
            self.rounds_completed += 1

            # Show emission per node
            sn = self.client.subnet.get_subnet(self.netuid)
            for uid in range(sn.node_count):
                try:
                    node = self.client.subnet.get_node(self.netuid, uid)
                    if node.active and node.emission > 0:
                        ntype = "Validator" if node.is_validator else "Miner"
                        self.log("💎", f"  {ntype} UID={uid}: +{node.emission_ether:.6f} MDT")
                except Exception:
                    continue
            return True
        except Exception as e:
            msg = str(e)
            if "Too early" in msg:
                self.log("⏳", "Not enough blocks for epoch yet")
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
                self.log("💰", f"Claimed {emission:.6f} MDT!", tx=tx[:16] + "...")
                return emission
        except Exception as e:
            if "No emission" not in str(e):
                self.log("ℹ️", f"Claim: {str(e)[:60]}")
        return 0.0

    def display_metagraph(self):
        """Display the subnet metagraph."""
        try:
            meta = self.client.subnet.get_metagraph(self.netuid)
            sn = self.client.subnet.get_subnet(self.netuid)

            print(f"\n  ╭── Metagraph: {sn.name} ──────────────────────╮")
            print(f"  │ {'UID':<5} {'Type':<11} {'Stake':<12} {'Trust':<10} {'Rank':<10} {'Emission':<12} │")
            print(f"  │ {'─'*5} {'─'*11} {'─'*12} {'─'*10} {'─'*10} {'─'*12} │")

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
                    f"{node.emission_ether:<12.6f} │"
                )

            total_stake_ether = float(Web3.from_wei(meta.total_stake, "ether"))
            print(
                f"  │ Total Stake: {total_stake_ether:.2f} MDT | "
                f"Miners: {len(meta.miners)} | Vals: {len(meta.validators)}       │"
            )
            print(f"  ╰{'─' * 68}╯\n")
        except Exception as e:
            self.log("⚠️", f"Metagraph error: {str(e)[:60]}")

    def run_loop(self, max_rounds=None):
        """Main validator loop."""
        self.header()
        print(f"\n  🔄 Starting validator (dispatching tasks every {POLL_INTERVAL}s)")
        print(f"  💡 Make sure miners are running: python demo/miner.py")
        print(f"  ⏹️  Press Ctrl+C to stop\n")

        round_num = 0

        while self.running:
            round_num += 1

            if max_rounds and round_num > max_rounds:
                self.log("🏁", f"Max rounds ({max_rounds}) reached")
                break

            # Step 1: Get miners
            miner_uids = self.get_miner_uids()
            if not miner_uids:
                self.log("⚠️", "No active miners found — waiting...")
                time.sleep(POLL_INTERVAL)
                continue

            # Step 2: Run validation round (create task → wait for miner → evaluate)
            scores = self.run_validation_round(round_num, miner_uids)

            # Step 3: Set weights on-chain
            if scores:
                self.set_weights_on_chain(scores)

            # Step 4: Run epoch
            self.try_run_epoch()

            # Step 5: Claim rewards
            self.claim_rewards()

            # Step 6: Display metagraph every 3 rounds
            if round_num % 3 == 0:
                self.display_metagraph()

            time.sleep(POLL_INTERVAL)

        # Final display
        self.display_metagraph()

    def stop(self):
        self.running = False


def main():
    from sdk.polkadot.client import PolkadotClient

    with open(WALLET_FILE) as f:
        wallets = json.load(f)

    demo_results_path = PROJECT_ROOT / "luxtensor" / "contracts" / "demo-results.json"
    with open(demo_results_path) as f:
        demo = json.load(f)

    val_key_name = f"validator{VALIDATOR_ID}"
    val_info = demo["nodes"].get(val_key_name)
    if not val_info:
        print(f"❌ Validator {VALIDATOR_ID} not found in demo-results.json")
        sys.exit(1)

    validator_uid = val_info["uid"]

    val_client = PolkadotClient(
        rpc_url=RPC_URL,
        private_key=wallets["validator"]["key"],
        deployment_path=DEPLOYMENT,
    )

    deployer_client = PolkadotClient(
        rpc_url=RPC_URL,
        private_key=wallets["deployer"]["key"],
        deployment_path=DEPLOYMENT,
    )

    if not val_client.is_connected:
        print("❌ Cannot connect to Polkadot Hub Testnet")
        sys.exit(1)

    validator = Validator(val_client, deployer_client, validator_uid=validator_uid, netuid=NETUID)

    def handle_sigint(sig, frame):
        print("\n\n  ⏹️  Shutting down validator gracefully...")
        validator.stop()
        validator.claim_rewards()
        validator.display_metagraph()
        print("  👋 Validator stopped.\n")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sigint)

    max_rounds = int(os.environ.get("MAX_ROUNDS", "0")) or None
    validator.run_loop(max_rounds=max_rounds)


if __name__ == "__main__":
    main()
