#!/usr/bin/env python3
"""
ModernTensor Subnet Demo — Full Proof-of-Intelligence Cycle.

Demonstrates the complete flow with miner + validator on a local node:
  1. Register validator + miner in subnet
  2. Validator creates AI inference task
  3. Miner processes task → model output + zkML proof
  4. Validator evaluates quality + sets weights
  5. Epoch distributes emission rewards

Prerequisites:
  cd luxtensor/contracts
  npx hardhat node                              # Terminal 1
  npx hardhat run scripts/deploy-all-local.js --network localhost  # Terminal 2
  python scripts/demo_subnet.py                 # Terminal 3
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web3 import Web3
from sdk.polkadot.client import PolkadotClient

# ── Hardhat default accounts ──
DEPLOYER_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
MINER_KEY = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
VALIDATOR_KEY = "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a"

DEPLOY_PATH = "luxtensor/contracts/deployments-local.json"
NETUID = 1


def banner(title, emoji="📋"):
    print()
    print(f"{'━' * 60}")
    print(f"  {emoji}  {title}")
    print(f"{'━' * 60}")


def main():
    print("=" * 60)
    print("  🧠 ModernTensor — Proof-of-Intelligence Demo")
    print("  Subnet Lifecycle: Register → Task → Prove → Score → Emit")
    print("=" * 60)

    # ── Setup clients ──
    banner("SETUP: Creating clients", "🔧")

    deployer = PolkadotClient(
        network="localhost",
        rpc_url="http://127.0.0.1:8545",
        private_key=DEPLOYER_KEY,
        deployment_path=DEPLOY_PATH,
    )
    miner_client = PolkadotClient(
        network="localhost",
        rpc_url="http://127.0.0.1:8545",
        private_key=MINER_KEY,
        deployment_path=DEPLOY_PATH,
    )
    validator_client = PolkadotClient(
        network="localhost",
        rpc_url="http://127.0.0.1:8545",
        private_key=VALIDATOR_KEY,
        deployment_path=DEPLOY_PATH,
    )

    print(f"  Deployer:  {deployer.address}")
    print(f"  Miner:     {miner_client.address}")
    print(f"  Validator: {validator_client.address}")
    print(f"  MDT balance (deployer): {deployer.token.balance_of_ether()} MDT")

    # ── Fund miner & validator with MDT ──
    banner("FUND: Transfer MDT tokens", "💰")

    for name, client in [("Miner", miner_client), ("Validator", validator_client)]:
        balance = client.token.balance_of_ether()
        if balance < 100:
            print(f"  Transferring 1000 MDT to {name}...")
            deployer.token.transfer(client.address, Web3.to_wei(1000, "ether"))
        print(f"  {name} MDT: {client.token.balance_of_ether()} MDT")

    # ── Create subnet (if not exists) ──
    banner("SUBNET: Create AI Subnet", "🌐")

    subnet_count = deployer.subnet.get_subnet_count()
    if subnet_count == 0:
        print("  Creating 'AI-Code-Review' subnet...")
        tx, netuid = deployer.subnet.create_subnet(
            name="AI-Code-Review",
            max_nodes=64,
            min_stake_ether=0,
            tempo=10,
        )
        print(f"  ✅ Subnet {netuid} created! TX: {tx[:16]}...")
    else:
        netuid = NETUID
        info = deployer.subnet.get_subnet(netuid)
        print(f"  Subnet {netuid}: name={info.name}, nodes={info.node_count}/{info.max_nodes}")

    # ── Register nodes ──
    banner("REGISTER: Validator + Miner", "📝")

    # Approve tokens for staking
    for name, client in [("Validator", validator_client), ("Miner", miner_client)]:
        client.token.approve(
            client._addresses["SubnetRegistry"],
            Web3.to_wei(500, "ether"),
        )

    # Register validator
    if not validator_client.subnet.is_registered(netuid):
        tx = validator_client.subnet.register_validator(netuid=netuid, stake_ether=100)
        print(f"  ✅ Validator registered! TX: {tx[:16]}...")
    else:
        print("  ✅ Validator already registered")

    # Register miner
    if not miner_client.subnet.is_registered(netuid):
        tx = miner_client.subnet.register_miner(netuid=netuid, stake_ether=100)
        print(f"  ✅ Miner registered! TX: {tx[:16]}...")
    else:
        print("  ✅ Miner already registered")

    # Show metagraph
    meta = deployer.subnet.get_metagraph(netuid)
    print(f"\n  📊 Metagraph: {len(meta.miners)} miners, {len(meta.validators)} validators")
    for n in meta.nodes:
        role = "VALIDATOR" if n.is_validator else "MINER"
        print(f"     UID {n.uid}: {role} | stake={n.total_stake_ether} MDT | trust={n.trust_float:.2f}")

    # ── Approve models + register miner as fulfiller ──
    banner("APPROVE: Models + Fulfiller", "🔑")

    models_to_approve = [
        "moderntensor-code-review-v1",
        "moderntensor-nlp-sentiment-v1",
        "moderntensor-risk-analysis-v1",
    ]
    for model_name in models_to_approve:
        model_hash = Web3.keccak(text=model_name)
        if not deployer.oracle.is_model_approved(model_hash):
            deployer.oracle.approve_model(model_hash)
            print(f"  ✅ Model approved: {model_name}")
        else:
            print(f"  ✅ Already approved: {model_name}")

    # Register miner + validator as fulfillers (F-08 requirement)
    oracle_contract = deployer._get_contract("AIOracle")
    for name, addr in [("Miner", miner_client.address), ("Validator", validator_client.address)]:
        try:
            tx = oracle_contract.functions.registerFulfiller(addr).build_transaction({})
            deployer.send_tx(tx)
            print(f"  ✅ {name} registered as fulfiller")
        except Exception:
            print(f"  ✅ {name} already fulfiller")

    # ── Run 3 Proof-of-Intelligence cycles ──
    orchestrator = validator_client.orchestrator(netuid=netuid)

    tasks = [
        {
            "name": "code-review-v1",
            "input": b"Review: function withdraw(uint a) external { payable(msg.sender).transfer(a); }",
        },
        {
            "name": "nlp-sentiment-v1",
            "input": b"Analyze sentiment: Polkadot Hub is revolutionizing cross-chain DeFi with parachain technology",
        },
        {
            "name": "risk-analysis-v1",
            "input": b"Assess risk: 50% DOT staking, 30% ETH liquidity pools, 20% governance tokens",
        },
    ]

    for i, task_def in enumerate(tasks, 1):
        banner(f"CYCLE {i}/3: {task_def['name']}", "🔄")

        # Step 1: Validator creates task
        print(f"  1. Validator creates task: {task_def['name']}")
        task = orchestrator.create_inference_task(
            model_name=task_def["name"],
            input_data=task_def["input"],
            payment_ether=0.01,
        )
        print(f"     Task ID: {task.task_id}")
        print(f"     Oracle TX: {task.oracle_tx[:16]}...")

        # Step 2: Miner processes task
        print(f"  2. Miner processes task (model + zkML proof)...")
        result = orchestrator.process_task(
            miner_client=miner_client,
            task=task,
            model_fn=None,  # Use simulation
            miner_uid=meta.miners[0].uid if meta.miners else 0,
        )
        print(f"     Output: {len(result.output)} bytes")
        print(f"     Proof verified: {result.proof_verified}")
        preview = result.output.decode("utf-8", errors="replace")[:80]
        print(f"     Preview: {preview}...")

        # Step 3: Validator evaluates
        print(f"  3. Validator evaluates quality + sets weights...")
        eval_result = orchestrator.evaluate_miners([result])
        print(f"     Average quality: {eval_result.average_quality:.3f}")
        print(f"     Verified proofs: {eval_result.verified_proofs}/{eval_result.total_tasks}")
        print(f"     Weights TX: {eval_result.weights_set_tx[:16]}...")
        for uid, score in eval_result.miner_scores.items():
            print(f"     Miner UID {uid}: weight={score:.3f}")

        print(f"  ✅ Cycle {i} complete!")

    # ── Trigger epoch ──
    banner("EPOCH: Distribute emission rewards", "🏆")

    try:
        epoch_tx = deployer.subnet.run_epoch(netuid)
        print(f"  ✅ Epoch distributed! TX: {epoch_tx[:16]}...")
    except Exception as e:
        print(f"  ⚠️  Epoch not ready: {e}")

    # ── Final metagraph ──
    banner("FINAL STATE", "📊")

    meta = deployer.subnet.get_metagraph(netuid)
    print(f"  Subnet {netuid}:")
    for n in meta.nodes:
        role = "VALIDATOR" if n.is_validator else "MINER"
        print(
            f"    UID {n.uid} [{role:>9}] | "
            f"stake={n.total_stake_ether:>8.1f} MDT | "
            f"rank={n.rank_float:.4f} | "
            f"trust={n.trust_float:.2f} | "
            f"emission={n.emission_ether:.4f} MDT"
        )

    print()
    print("=" * 60)
    print("  🎉 Demo complete! 3 Proof-of-Intelligence cycles executed.")
    print("  Miners earned rewards based on verified AI quality.")
    print("=" * 60)


if __name__ == "__main__":
    main()
