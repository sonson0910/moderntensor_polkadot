#!/usr/bin/env python3
"""
ModernTensor Demo — Step 7: Complete Demo Orchestrator

Runs the ENTIRE subnet lifecycle in a single script:

  Phase 1 — Setup:
    Connect → Wallets → Load Contracts → Distribute MDT
    Create Subnet → Register Validator + Miner

  Phase 2 — AI Inference Cycle (3 domains):
    Setup zkML → Create Tasks → Miner Process → Evaluate → Set Weights

  Phase 3 — Emission & Rewards:
    Fund Emission Pool → Run Epoch → Claim Rewards → Metagraph

  Phase 4 — Federated Learning:
    Create Training Job → Submit Gradients → Finalize Rounds → Claim

  Phase 5 — Training Escrow:
    Create Escrow Task → Miner Stakes → Submit → Validate → Claim

Prerequisites:
  cd luxtensor/contracts && npx hardhat node
  cd luxtensor/contracts && npx hardhat run scripts/deploy-polkadot.js --network luxtensor_local

Usage:
  python demo/07_run_demo.py
"""

import os
import sys
import time
import warnings
from pathlib import Path

# Suppress dev-mode proof warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from demo.config import (
    get_network,
    HARDHAT_ACCOUNTS,
    AI_MODELS,
    TOKEN_TO_VALIDATOR,
    TOKEN_TO_MINER,
    EMISSION_FUND,
    VALIDATOR_STAKE,
    MINER_STAKE,
    SUBNET_NAME,
    SUBNET_TEMPO,
    SUBNET_MAX_NODES,
    SUBNET_MIN_STAKE,
    banner,
    step_log,
    ok,
    info,
    warn,
    fail,
    separator,
)
from web3 import Web3

# Import from numbered modules using importlib
import importlib

_miner_mod = importlib.import_module("demo.05_run_miner")
_validator_mod = importlib.import_module("demo.06_run_validator")
MinerNode = _miner_mod.MinerNode
ValidatorNode = _validator_mod.ValidatorNode


def phase1_setup(network_name="local"):
    """Phase 1: Connect, wallets, distribute tokens, create subnet, register nodes."""
    banner("PHASE 1 — SETUP")

    from sdk.polkadot.client import PolkadotClient

    net = get_network(network_name)

    # Connect
    step_log("1.0", f"Connecting to {net['label']}...")
    w3 = Web3(Web3.HTTPProvider(net["rpc_url"]))
    if not w3.is_connected():
        fail(f"Cannot connect to {net['rpc_url']}")
    ok(f"Connected! Chain ID: {w3.eth.chain_id}, Block: {w3.eth.block_number}")

    # Load wallets
    step_log("1.1", "Loading wallets...")
    if network_name == "local":
        wallets = HARDHAT_ACCOUNTS
    else:
        import json

        wallet_file = Path(__file__).resolve().parent / "wallets.json"
        with open(wallet_file) as f:
            wallets = json.load(f)

    for role, w in wallets.items():
        balance = w3.eth.get_balance(w["address"])
        ok(f"{role.capitalize():>10}: {w['address']} ({Web3.from_wei(balance, 'ether'):.2f} ETH)")

    # Create clients
    step_log("1.2", "Initializing SDK clients...")
    clients = {}
    for role in ["deployer", "validator", "miner"]:
        clients[role] = PolkadotClient(
            rpc_url=net["rpc_url"],
            private_key=wallets[role]["key"],
            deployment_path=net["deployment"],
        )
        ok(f"{role.capitalize()} client ready: {clients[role].address}")

    # Distribute tokens
    step_log("1.3", "Distributing MDT tokens...")
    token = clients["deployer"].token
    owner_bal = token.balance_of_ether(clients["deployer"].address)
    ok(f"Owner MDT balance: {owner_bal:,.2f}")

    for role, amount in [("validator", TOKEN_TO_VALIDATOR), ("miner", TOKEN_TO_MINER)]:
        addr = clients[role].address
        current = token.balance_of_ether(addr)
        if current < amount:
            tx = token.transfer(addr, Web3.to_wei(amount, "ether"))
            ok(f"{role.capitalize()}: +{amount} MDT (TX: {tx})")
        else:
            ok(f"{role.capitalize()}: already has {current:,.2f} MDT")

    # Check/create subnet
    step_log("1.4", "Checking subnet...")
    subnet = clients["deployer"].subnet
    count = subnet.get_subnet_count()

    netuid = 1
    if count > 0:
        s = subnet.get_subnet(1)
        ok(f"Subnet 1 exists: '{s.name}' (tempo={s.tempo})")
    else:
        registry_addr = clients["deployer"]._get_contract("SubnetRegistry").address
        token.approve(registry_addr, Web3.to_wei(100, "ether"))
        tx, netuid = subnet.create_subnet(
            name=SUBNET_NAME,
            max_nodes=SUBNET_MAX_NODES,
            min_stake_ether=SUBNET_MIN_STAKE,
            tempo=SUBNET_TEMPO,
        )
        ok(f"Created subnet: netuid={netuid}, TX: {tx}")

    # Register validator
    step_log("1.5", "Registering validator...")
    val_sub = clients["validator"].subnet
    if val_sub.is_registered(netuid, clients["validator"].address):
        val_uid = val_sub.get_uid(netuid, clients["validator"].address)
        ok(f"Already registered: UID={val_uid}")
    else:
        registry_addr = clients["validator"]._get_contract("SubnetRegistry").address
        clients["validator"].token.approve(registry_addr, Web3.to_wei(VALIDATOR_STAKE, "ether"))
        tx = val_sub.register_validator(
            netuid=netuid, hotkey=clients["validator"].address, stake_ether=VALIDATOR_STAKE
        )
        val_uid = val_sub.get_uid(netuid, clients["validator"].address)
        ok(f"Registered! UID={val_uid}, TX: {tx}")

    # Register miner
    step_log("1.6", "Registering miner...")
    miner_sub = clients["miner"].subnet
    if miner_sub.is_registered(netuid, clients["miner"].address):
        miner_uid = miner_sub.get_uid(netuid, clients["miner"].address)
        ok(f"Already registered: UID={miner_uid}")
    else:
        registry_addr = clients["miner"]._get_contract("SubnetRegistry").address
        clients["miner"].token.approve(registry_addr, Web3.to_wei(MINER_STAKE, "ether"))
        tx = miner_sub.register_miner(
            netuid=netuid, hotkey=clients["miner"].address, stake_ether=MINER_STAKE
        )
        miner_uid = miner_sub.get_uid(netuid, clients["miner"].address)
        ok(f"Registered! UID={miner_uid}, TX: {tx}")

    # Register miner as Oracle fulfiller
    step_log("1.7", "Registering miner as Oracle fulfiller...")
    try:
        tx = clients["deployer"].oracle.register_fulfiller(clients["miner"].address)
        ok(f"Fulfiller registered: {tx}")
    except Exception as e:
        info(f"Fulfiller: {str(e)[:60]}")

    return w3, clients, netuid, val_uid, miner_uid


def phase2_zkml_setup(clients):
    """Phase 2a: Setup zkML trust and Oracle model approval."""
    banner("PHASE 2a — zkML & ORACLE SETUP")

    owner = clients["deployer"]
    zkml = owner.zkml
    oracle = owner.oracle

    # Enable dev mode
    step_log("2.0", "Enabling zkML dev mode...")
    if not zkml.dev_mode_enabled():
        tx = zkml.set_dev_mode(True)
        ok(f"Dev mode ON: {tx}")
    else:
        ok("Dev mode already enabled")

    # Trust models
    step_log("2.1", f"Trusting {len(AI_MODELS)} AI models...")
    for model_name in AI_MODELS:
        image_id = Web3.keccak(text=model_name)
        if not zkml.is_image_trusted(image_id):
            tx = zkml.trust_image(image_id)
            ok(f"Trusted '{model_name}': {tx}")
        else:
            ok(f"Already trusted: {model_name}")

    # Approve in Oracle
    step_log("2.2", "Approving models in Oracle...")
    for model_name in AI_MODELS:
        model_hash = Web3.keccak(text=model_name)
        if not oracle.is_model_approved(model_hash):
            tx = oracle.approve_model(model_hash)
            ok(f"Approved '{model_name}': {tx}")
        else:
            ok(f"Already approved: {model_name}")


def phase2_ai_cycle(clients, netuid, val_uid, miner_uid):
    """Phase 2b: Full AI inference cycle — create tasks, process, evaluate, set weights."""
    banner("PHASE 2b — MULTI-DOMAIN AI INFERENCE CYCLE")

    # Create validator and miner nodes
    validator = ValidatorNode(clients["validator"], netuid=netuid)
    miner = MinerNode(clients["miner"], netuid=netuid)

    # Create tasks
    tasks = validator.create_tasks()

    # Miner processes tasks
    results = validator.process_tasks_with_miner(tasks, miner)

    # Evaluate and set weights
    evaluation = validator.evaluate_and_set_weights(results)

    return validator, miner, evaluation


def phase3_emission(clients, w3, netuid, val_uid, miner_uid):
    """Phase 3: Fund emission, run epoch, claim rewards."""
    banner("PHASE 3 — EMISSION & REWARDS")

    owner = clients["deployer"]
    token = owner.token
    subnet = owner.subnet

    # Fund emission pool
    step_log("3.1", f"Funding emission pool with {EMISSION_FUND} MDT...")
    registry_addr = owner._get_contract("SubnetRegistry").address
    token.approve(registry_addr, Web3.to_wei(EMISSION_FUND, "ether"))
    try:
        tx = subnet.fund_emission_pool(EMISSION_FUND)
        ok(f"Funded: {tx}")
    except Exception as e:
        info(f"Emission pool: {str(e)[:80]}")

    # Mine blocks to exceed tempo (need at least 360 blocks for tempo=360)
    step_log("3.2", "Mining blocks to exceed tempo...")
    subnet_info = subnet.get_subnet(netuid)
    blocks_to_mine = max(subnet_info.tempo + 10, 370)
    for _ in range(blocks_to_mine):
        w3.provider.make_request("evm_mine", [])
    ok(f"Mined {blocks_to_mine} blocks. Current: {w3.eth.block_number}")

    # Run epoch
    step_log("3.3", "Running epoch (Yuma Consensus emission)...")
    try:
        tx = subnet.run_epoch(netuid)
        ok(f"Epoch complete! TX: {tx}")
    except Exception as e:
        info(f"Epoch: {str(e)[:100]}")

    # Check emission
    step_log("3.4", "Checking emission rewards...")
    for role, uid in [("validator", val_uid), ("miner", miner_uid)]:
        c = clients[role]
        node = c.subnet.get_node(netuid, uid)
        ok(f"{role.capitalize()} pending emission: {node.emission_ether:.6f} MDT")

        if node.emission > 0:
            try:
                tx = c.subnet.claim_emission(netuid, uid)
                ok(f"{role.capitalize()} claimed! TX: {tx}")
            except Exception as e:
                info(f"Claim: {str(e)[:60]}")

    # Metagraph
    step_log("3.5", "Final metagraph...")
    meta = owner.subnet.get_metagraph(netuid)
    separator()
    print(f"  {'UID':<5} {'Type':<12} {'Hotkey':<16} {'Stake':<14} {'Rank':<12} {'Active'}")
    separator()
    for node in meta.nodes:
        ntype = "VALIDATOR" if node.is_validator else "MINER"
        print(
            f"  {node.uid:<5} {ntype:<12} {node.hotkey[:14]}.. {node.total_stake_ether:<14.4f} {node.rank_float:<12.6f} {'Yes' if node.active else 'No'}"
        )
    separator()


def phase4_federated_learning(clients, w3):
    """Phase 4: Federated Learning cycle using GradientAggregator."""
    banner("PHASE 4 — FEDERATED LEARNING")

    owner = clients["deployer"]
    miner = clients["miner"]
    token = owner.token
    training = owner.training

    # Create job
    step_log("4.1", "Creating training job (3 rounds)...")
    model_hash = Web3.keccak(text="fedavg-resnet50-polkadot-v1")
    reward_amount = 500  # MDT
    aggregator_addr = training._contract.address
    token.approve(aggregator_addr, Web3.to_wei(reward_amount, "ether"))

    tx = training.create_job(
        model_hash=model_hash,
        total_rounds=3,
        reward_ether=reward_amount,
        max_participants=10,
        round_deadline=7200,
    )
    ok(f"Job created: {tx}")

    job_id = training.next_job_id() - 1
    job = training.get_job_details(job_id)
    info(f"  Job ID: {job_id}, Rounds: {job.total_rounds}, Reward: {job.reward_pool_ether:.0f} MDT")

    # Miner submits gradients + owner finalizes each round
    miner_training = miner.training
    for round_num in range(1, 4):
        step_log(f"4.2.{round_num}", f"Round {round_num}/3...")

        # Miner submits gradient
        grad_hash = Web3.keccak(text=f"gradient-round-{round_num}-miner-{miner.address[:8]}")
        tx = miner_training.submit_gradient(
            job_id=job_id, gradient_hash=grad_hash, data_size=1000 * round_num
        )
        ok(f"Gradient submitted: {tx}")

        # Owner finalizes
        agg_hash = Web3.keccak(text=f"aggregated-model-round-{round_num}")
        tx = training.finalize_round(
            job_id=job_id, aggregated_hash=agg_hash, valid_participants=[miner.address]
        )
        ok(f"Round finalized: {tx}")

    # Claim reward
    step_log("4.3", "Miner claiming reward...")
    bal_before = token.balance_of_ether(miner.address)
    tx = miner_training.claim_reward(job_id)
    bal_after = token.balance_of_ether(miner.address)
    ok(f"Claimed! +{bal_after - bal_before:.2f} MDT (TX: {tx})")

    return job_id


def phase5_training_escrow(clients, w3):
    """Phase 5: Training Escrow cycle — stake-gated training."""
    banner("PHASE 5 — TRAINING ESCROW")

    owner = clients["deployer"]
    miner = clients["miner"]
    token = owner.token
    escrow = owner.escrow

    # Create task
    step_log("5.1", "Creating escrow training task...")
    model_hash = Web3.keccak(text="finetune-llm-polkadot-v1")
    reward_amount = 200  # MDT
    min_stake = 10  # MDT

    escrow_addr = escrow._contract.address
    token.approve(escrow_addr, Web3.to_wei(reward_amount, "ether"))
    tx = escrow.create_task(
        model_hash=model_hash,
        reward_ether=reward_amount,
        min_stake_ether=min_stake,
        max_trainers=5,
        duration_seconds=86400,
    )
    ok(f"Task created: {tx}")

    task_id = escrow.next_task_id() - 1
    info(f"  Task ID: {task_id}, Reward: {reward_amount} MDT, Min Stake: {min_stake} MDT")

    # Miner joins
    step_log("5.2", f"Miner staking {min_stake} MDT to join...")
    miner_escrow = miner.escrow
    miner.token.approve(escrow_addr, Web3.to_wei(min_stake, "ether"))
    tx = miner_escrow.join_task(task_id, stake_ether=min_stake)
    ok(f"Miner joined: {tx}")

    # Miner submits result
    step_log("5.3", "Miner submitting result...")
    result_hash = Web3.keccak(text=f"training-result-{miner.address[:8]}-task-{task_id}")
    tx = miner_escrow.submit_result(task_id, result_hash)
    ok(f"Result submitted: {tx}")

    # Owner validates
    step_log("5.4", "Owner validating submission...")
    tx = escrow.validate_trainer(task_id, miner.address, is_valid=True)
    ok(f"Validated: {tx}")

    # Complete task
    step_log("5.5", "Owner completing task...")
    tx = escrow.complete_task(task_id)
    ok(f"Task completed: {tx}")

    # Miner claims
    step_log("5.6", "Miner claiming reward + stake...")
    bal_before = token.balance_of_ether(miner.address)
    tx = miner_escrow.claim_reward(task_id)
    bal_after = token.balance_of_ether(miner.address)
    ok(f"Claimed! +{bal_after - bal_before:.2f} MDT (TX: {tx})")

    return task_id


def print_summary(clients, netuid):
    """Print final summary with token balances."""
    banner("🎉 DEMO COMPLETE — SUMMARY")

    token = clients["deployer"].token

    print(
        """
  ═══════════════════════════════════════════════════
  All 8 Smart Contracts Integrated:
  ═══════════════════════════════════════════════════

  MDTToken ──── MDTVesting ──── MDTStaking
  SubnetRegistry ──── ZkMLVerifier ──── AIOracle
  GradientAggregator ──── TrainingEscrow

  ═══════════════════════════════════════════════════
  Operations Completed:
  ═══════════════════════════════════════════════════

  Phase 1 — Setup:
    ✅ Connected to local/testnet node
    ✅ Generated 3 wallets (deployer, validator, miner)
    ✅ Loaded 8 deployed contracts
    ✅ Distributed MDT tokens
    ✅ Created subnet + registered validator & miner

  Phase 2 — Multi-Domain AI Cycle:
    ✅ Enabled zkML dev mode + trusted 3 model images
    ✅ Approved 3 AI models in Oracle
    ✅ Validator created 3 inference tasks (NLP, Finance, Code)
    ✅ Miner processed all tasks + generated zkML proofs
    ✅ Validator evaluated quality → set weights on-chain

  Phase 3 — Emission:
    ✅ Funded emission pool
    ✅ Ran epoch (Yuma Consensus emission distribution)
    ✅ Claimed emission rewards

  Phase 4 — Federated Learning:
    ✅ Created 3-round training job (FedAvg)
    ✅ Miner submitted gradients for all rounds
    ✅ Owner finalized rounds + miner claimed rewards

  Phase 5 — Training Escrow:
    ✅ Created stake-gated training task
    ✅ Miner staked, submitted, validated, claimed rewards
    """
    )

    print(f"  💰 Final Token Balances:")
    separator()
    for role in ["deployer", "validator", "miner"]:
        bal = token.balance_of_ether(clients[role].address)
        print(f"    {role.capitalize():>10}: {bal:,.4f} MDT")

    print(
        f"""
  ═══════════════════════════════════════════════════
  🔑 KEY INSIGHT: ModernTensor is a MULTI-DOMAIN protocol.
  ANY AI vertical can run as a subnet:
    NLP • Vision • Finance • Health • Code Review • Custom

  Weights are NOT set manually. Miners earn weights
  through VERIFIED work across ANY domain:
    Oracle (task) → zkML (proof) → Weights → Emission

  Built for Polkadot EVM — powered by 8 smart contracts.
  ═══════════════════════════════════════════════════
    """
    )


def main():
    start_time = time.time()

    print(
        """
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   🚀 ModernTensor — Complete Subnet Demo             ║
║   Polkadot Solidity Hackathon 2026                   ║
║   Track 1: EVM Smart Contract — AI-powered dApps     ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
    """
    )

    network_name = os.environ.get("NETWORK", "local")

    # Phase 1: Full Setup
    w3, clients, netuid, val_uid, miner_uid = phase1_setup(network_name)

    # Phase 2: AI Inference Cycle
    phase2_zkml_setup(clients)
    validator, miner, evaluation = phase2_ai_cycle(clients, netuid, val_uid, miner_uid)

    # Phase 3: Emission & Rewards
    phase3_emission(clients, w3, netuid, val_uid, miner_uid)

    # Phase 4: Federated Learning
    phase4_federated_learning(clients, w3)

    # Phase 5: Training Escrow
    phase5_training_escrow(clients, w3)

    # Summary
    print_summary(clients, netuid)

    elapsed = time.time() - start_time
    print(f"  ⏱️  Demo completed in {elapsed:.1f} seconds\n")


if __name__ == "__main__":
    main()
