#!/usr/bin/env python3
"""
ModernTensor Auto Demo — Chạy 1 lệnh
═══════════════════════════════════════

Tự động chạy Miner + Validator cùng lúc, hiển thị logs và kết quả on-chain.

Usage:
  python subnet/run_demo.py              # Chạy 3 rounds mặc định
  python subnet/run_demo.py 5            # Chạy 5 rounds
"""

import os
import sys
import time
import json
import signal
import subprocess
from pathlib import Path
from datetime import datetime

SUBNET_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SUBNET_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

CONFIG_FILE = SUBNET_DIR / "config.json"
with open(CONFIG_FILE) as f:
    CFG = json.load(f)


def log(emoji, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"  [{ts}] {emoji} {msg}")


def clear_task_queue():
    """Clean up old tasks."""
    task_dir = SUBNET_DIR / "task_queue"
    task_dir.mkdir(exist_ok=True)
    for f in task_dir.glob("task_*.json"):
        f.unlink()


def main():
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 3

    print()
    print("╔" + "═" * 62 + "╗")
    print("║  🚀  ModernTensor SUBNET DEMO                                 ║")
    print("║  Polkadot Hub Testnet — Automated Demo                        ║")
    print("╚" + "═" * 62 + "╝")
    print(f"  Network:    {CFG['network']['name']}")
    print(f"  Subnet:     {CFG['subnet']['name']} (netuid={CFG['subnet']['netuid']})")
    print(f"  Rounds:     {rounds}")
    print(f"  Miners:     {[k for k in CFG['nodes'] if 'miner' in k]}")
    print(f"  Validators: {[k for k in CFG['nodes'] if 'validator' in k]}")
    print("─" * 64)

    # Step 1: Query initial state
    log("📊", "Step 1/5 — Querying initial on-chain state...")
    try:
        subprocess.run(
            [sys.executable, str(SUBNET_DIR / "query_chain.py"), "metagraph"],
            cwd=str(PROJECT_ROOT),
            timeout=30,
        )
    except Exception as e:
        log("⚠️", f"Query error: {e}")

    # Step 2: Clear old tasks
    log("🧹", "Step 2/5 — Clearing task queue...")
    clear_task_queue()
    log("✅", "Task queue cleared")

    # Step 3: Start miner in background
    log("⛏️", "Step 3/5 — Starting Miner (background process)...")
    env = os.environ.copy()
    env["MAX_ROUNDS"] = str(rounds)
    env["MINER_ID"] = "1"

    miner_proc = subprocess.Popen(
        [sys.executable, str(SUBNET_DIR / "miner_node.py")],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    log("✅", f"Miner started (PID={miner_proc.pid})")

    # Step 4: Start validator in foreground
    log("🔷", "Step 4/5 — Starting Validator (foreground)...")
    time.sleep(2)  # Give miner time to initialize

    env2 = os.environ.copy()
    env2["MAX_ROUNDS"] = str(rounds)
    env2["VALIDATOR_ID"] = "1"

    try:
        val_proc = subprocess.run(
            [sys.executable, str(SUBNET_DIR / "validator_node.py")],
            cwd=str(PROJECT_ROOT),
            env=env2,
            timeout=rounds * 60,
        )
    except subprocess.TimeoutExpired:
        log("⏰", "Validator timeout — stopping")
    except KeyboardInterrupt:
        log("⏹️", "Demo interrupted")

    # Step 5: Show miner output
    log("📄", "Step 5/5 — Miner output:")
    print("─" * 64)
    try:
        miner_proc.wait(timeout=10)
        output = miner_proc.stdout.read()
        print(output)
    except Exception:
        miner_proc.terminate()
        try:
            output = miner_proc.stdout.read()
            print(output)
        except Exception:
            pass
    print("─" * 64)

    # Final: Query updated state
    log("📊", "Final — Querying updated on-chain state...")
    try:
        subprocess.run(
            [sys.executable, str(SUBNET_DIR / "query_chain.py")],
            cwd=str(PROJECT_ROOT),
            timeout=30,
        )
    except Exception:
        pass

    print()
    log("🏁", "Demo complete!")
    print()


if __name__ == "__main__":
    main()
