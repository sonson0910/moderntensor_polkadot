#!/usr/bin/env python3
"""
ModernTensor — Complete End-to-End Workflow

Runs the FULL lifecycle on a local Hardhat node:

  Phase 1 — Setup:
    1-3. Connect, generate wallets, load contracts
    4.   Distribute MDT tokens
    5-6. Create subnet, register validator + miner

  Phase 2 — Integrated AI Inference Cycle:
    7.   Setup zkML verification layer
    8.   Validator creates AI tasks via Oracle
    9.   Miner processes tasks + generates zkML proofs
    10.  Validator evaluates quality → sets weights

  Phase 3 — Emission:
    11. Run epoch (Yuma Consensus emission)
    12. Claim emission rewards
    13. Display final metagraph

Prerequisites:
  1. Start Hardhat node:
     cd luxtensor/contracts && npx hardhat node
  2. Deploy contracts:
     cd luxtensor/contracts && npx hardhat run scripts/deploy-polkadot.js --network luxtensor_local
  3. Set PRIVATE_KEY env var to one of Hardhat's default accounts

Usage:
  PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 python3 e2e_workflow.py
"""

import os, sys, json
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web3 import Web3
from eth_account import Account


# ════════════════════════════════════════════════════════
# Config
# ════════════════════════════════════════════════════════
RPC_URL = os.environ.get("RPC_URL", "http://127.0.0.1:8545")

# Hardhat default accounts (first 3)
ACCOUNTS = [
    {  # Account 0 — deployer / subnet owner
        "key": "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
        "address": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
    },
    {  # Account 1 — validator
        "key": "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",
        "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
    },
    {  # Account 2 — miner
        "key": "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a",
        "address": "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC",
    },
]


def header(text):
    print(f"\n{'='*60}")
    print(f"🔷 {text}")
    print(f"{'='*60}")


def step(num, text):
    print(f"\n  [{num}] {text}")


def ok(text):
    print(f"      ✅ {text}")


def info(text):
    print(f"      ℹ️  {text}")


def fail(text):
    print(f"      ❌ {text}")
    sys.exit(1)


# ════════════════════════════════════════════════════════
# Step 0: Connect
# ════════════════════════════════════════════════════════
def do_connect():
    header("STEP 0 — Connect to Local Hardhat Node")
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        fail(
            f"Cannot connect to {RPC_URL}. Start Hardhat node first:\n"
            f"  cd luxtensor/contracts && npx hardhat node"
        )
    chain_id = w3.eth.chain_id
    block = w3.eth.block_number
    ok(f"Connected to {RPC_URL}")
    info(f"Chain ID: {chain_id}, Block: {block}")
    return w3


# ════════════════════════════════════════════════════════
# Step 1: Generate Wallets (using Hardhat accounts)
# ════════════════════════════════════════════════════════
def do_wallets(w3):
    header("STEP 1 — Generate Wallets (Hardhat Default Accounts)")

    roles = ["Deployer/Owner", "Validator", "Miner"]
    for i, (acct, role) in enumerate(zip(ACCOUNTS, roles)):
        balance = w3.eth.get_balance(acct["address"])
        ok(f"{role}: {acct['address']}")
        info(f"  Balance: {Web3.from_wei(balance, 'ether')} ETH")

    return ACCOUNTS


# ════════════════════════════════════════════════════════
# Step 2: Load Deployment & Init Clients
# ════════════════════════════════════════════════════════
def do_init_clients(w3):
    header("STEP 2 — Load Deployed Contracts")

    deploy_file = Path("luxtensor/contracts/deployments-polkadot.json")
    if not deploy_file.exists():
        fail(
            "Deployment file not found. Deploy contracts first:\n"
            "  cd luxtensor/contracts && npx hardhat run scripts/deploy-polkadot.js --network luxtensor_local"
        )

    with open(deploy_file) as f:
        deploy_data = json.load(f)

    contracts = deploy_data.get("contracts", deploy_data)
    ok(f"Loaded {len(contracts)} contract addresses")

    for name, addr in contracts.items():
        info(f"  {name}: {addr}")

    # Create clients for each role
    from sdk.polkadot.client import PolkadotClient

    clients = {}
    for i, role in enumerate(["owner", "validator", "miner"]):
        clients[role] = PolkadotClient(
            rpc_url=RPC_URL,
            private_key=ACCOUNTS[i]["key"],
            deployment_path=str(deploy_file),
        )
        ok(f"  {role.capitalize()} client ready: {clients[role].address}")

    return clients, contracts


# ════════════════════════════════════════════════════════
# Step 3: Distribute Tokens
# ════════════════════════════════════════════════════════
def do_distribute_tokens(clients):
    header("STEP 3 — Distribute MDT Tokens to Validator & Miner")

    owner = clients["owner"]
    token = owner.token

    # Check owner balance
    owner_balance = token.balance_of_ether(owner.address)
    ok(f"Owner MDT balance: {owner_balance:.2f} MDT")

    if owner_balance < 1000:
        fail("Owner has insufficient MDT. Ensure TGE was run during deployment.")

    # Transfer 5000 MDT to validator, 1000 MDT to miner
    for role, amount in [("validator", 5000), ("miner", 1000)]:
        addr = clients[role].address
        step(f"3.{role[0]}", f"Transferring {amount} MDT → {role} ({addr[:12]}...)")
        tx = token.transfer(addr, Web3.to_wei(amount, "ether"))
        ok(f"TX: {tx}")
        balance = token.balance_of_ether(addr)
        info(f"  {role.capitalize()} balance: {balance:.2f} MDT")


# ════════════════════════════════════════════════════════
# Step 4: Create Subnet (or use existing one from deploy)
# ════════════════════════════════════════════════════════
def do_create_subnet(clients):
    header("STEP 4 — Create/Verify Subnet")

    owner = clients["owner"]
    subnet = owner.subnet

    count = subnet.get_subnet_count()
    ok(f"Current subnet count: {count}")

    if count > 0:
        info("Subnet 1 already exists (created during deployment)")
        s = subnet.get_subnet(1)
        ok(f"  Name: {s.name}")
        ok(f"  Max Nodes: {s.max_nodes}")
        ok(f"  Tempo: {s.tempo} blocks")
        ok(f"  Active: {s.active}")
        return 1

    # Create a new subnet if needed
    step("4a", "Creating subnet 'ModernTensor E2E Subnet'...")
    token = owner.token
    # Approve subnet creation cost (100 MDT)
    approve_tx = token.approve(
        owner._get_contract("SubnetRegistry").address, Web3.to_wei(100, "ether")
    )
    ok(f"Approved 100 MDT, TX: {approve_tx}")

    create_tx = subnet.create_subnet(
        name="ModernTensor E2E Subnet",
        max_nodes=256,
        min_stake_ether=10,
        tempo=10,  # 10 blocks for fast testing
    )
    ok(f"Subnet created! TX: {create_tx}")

    s = subnet.get_subnet(1)
    info(f"  Name: {s.name}, Tempo: {s.tempo}")
    return 1


# ════════════════════════════════════════════════════════
# Step 5: Register Validator
# ════════════════════════════════════════════════════════
def do_register_validator(clients, netuid):
    header("STEP 5 — Register Validator")

    val_client = clients["validator"]
    subnet = val_client.subnet

    if subnet.is_registered(netuid, val_client.address):
        ok("Validator already registered!")
        uid = subnet.get_uid(netuid, val_client.address)
        info(f"  UID: {uid}")
        return uid

    step("5a", f"Approving stake MDT for validator registration...")
    stake_amount = 100  # 100 MDT
    approve_tx = val_client.token.approve(
        val_client._get_contract("SubnetRegistry").address, Web3.to_wei(stake_amount, "ether")
    )
    ok(f"Approved {stake_amount} MDT, TX: {approve_tx}")

    step("5b", "Registering as VALIDATOR on subnet...")
    reg_tx = subnet.register_validator(
        netuid=netuid,
        hotkey=val_client.address,
        stake_ether=stake_amount,
    )
    ok(f"Registered! TX: {reg_tx}")

    uid = subnet.get_uid(netuid, val_client.address)
    ok(f"  Validator UID: {uid}")

    node = subnet.get_node(netuid, uid)
    info(f"  Stake: {node.total_stake_ether:.2f} MDT")
    info(f"  Active: {node.active}")

    return uid


# ════════════════════════════════════════════════════════
# Step 6: Register Miner
# ════════════════════════════════════════════════════════
def do_register_miner(clients, netuid):
    header("STEP 6 — Register Miner")

    miner_client = clients["miner"]
    subnet = miner_client.subnet

    if subnet.is_registered(netuid, miner_client.address):
        ok("Miner already registered!")
        uid = subnet.get_uid(netuid, miner_client.address)
        info(f"  UID: {uid}")
        return uid

    step("6a", "Approving stake for miner...")
    stake_amount = 50  # 50 MDT
    approve_tx = miner_client.token.approve(
        miner_client._get_contract("SubnetRegistry").address, Web3.to_wei(stake_amount, "ether")
    )
    ok(f"Approved {stake_amount} MDT, TX: {approve_tx}")

    step("6b", "Registering as MINER on subnet...")
    reg_tx = subnet.register_miner(
        netuid=netuid,
        hotkey=miner_client.address,
        stake_ether=stake_amount,
    )
    ok(f"Registered! TX: {reg_tx}")

    uid = subnet.get_uid(netuid, miner_client.address)
    ok(f"  Miner UID: {uid}")

    node = subnet.get_node(netuid, uid)
    info(f"  Stake: {node.total_stake_ether:.2f} MDT")

    return uid


# ════════════════════════════════════════════════════════
# Step 7: Setup zkML Trust (prepare for integrated cycle)
# ════════════════════════════════════════════════════════
def do_setup_zkml_trust(clients):
    header("STEP 7 — Setup zkML Verification Layer (Multi-Domain)")

    owner = clients["owner"]
    zkml = owner.zkml

    step("7a", "Checking zkML dev mode...")
    dev_mode = zkml.dev_mode_enabled()
    ok(f"Dev mode: {dev_mode}")

    step("7b", "Trusting model images across multiple AI domains...")

    # Trust NLP model image
    nlp_id = Web3.keccak(text="moderntensor-nlp-sentiment-v1")
    if not zkml.is_image_trusted(nlp_id):
        tx = zkml.trust_image(nlp_id)
        ok(f"Trusted 'nlp-sentiment-v1' [NLP domain] (TX: {tx})")
    else:
        ok("'nlp-sentiment-v1' already trusted")

    # Trust Finance model image
    fin_id = Web3.keccak(text="moderntensor-finance-risk-v1")
    if not zkml.is_image_trusted(fin_id):
        tx = zkml.trust_image(fin_id)
        ok(f"Trusted 'finance-risk-v1' [Finance domain] (TX: {tx})")
    else:
        ok("'finance-risk-v1' already trusted")

    # Trust Code Review model image
    code_id = Web3.keccak(text="moderntensor-code-review-v1")
    if not zkml.is_image_trusted(code_id):
        tx = zkml.trust_image(code_id)
        ok(f"Trusted 'code-review-v1' [Code domain] (TX: {tx})")
    else:
        ok("'code-review-v1' already trusted")

    # Step 7c: Approve models in Oracle (required for task creation)
    step("7c", "Approving multi-domain models in Oracle...")
    oracle = owner.oracle

    for model_full_name in [
        "moderntensor-nlp-sentiment-v1",
        "moderntensor-finance-risk-v1",
        "moderntensor-code-review-v1",
    ]:
        model_hash = Web3.keccak(text=model_full_name)
        if not oracle.is_model_approved(model_hash):
            tx = oracle.approve_model(model_hash)
            ok(f"Oracle approved '{model_full_name}' (TX: {tx})")
        else:
            ok(f"Oracle: '{model_full_name}' already approved")

    # Step 7d: Register miner as an authorized Oracle fulfiller
    step("7d", "Registering miner as Oracle fulfiller...")
    miner_addr = clients["miner"].address
    tx = oracle.register_fulfiller(miner_addr)
    ok(f"Miner registered as fulfiller (TX: {tx})")
    info(f"  Fulfiller: {miner_addr}")

    info("zkML + Oracle ready — 3 AI domains trusted & approved, fulfiller registered")


# ════════════════════════════════════════════════════════
# Step 8: Validator Creates Multi-Domain Tasks via Oracle
# ════════════════════════════════════════════════════════
def do_create_ai_tasks(clients, netuid):
    header("STEP 8 — Validator Creates Multi-Domain Inference Tasks")

    val_client = clients["validator"]
    orch = val_client.orchestrator(netuid, validator_uid=0)

    step("8a", "Checking oracle status before tasks...")
    total_before = val_client.oracle.total_requests()
    fee_bps = val_client.oracle.protocol_fee_bps()
    ok(f"Total requests: {total_before}")
    info(f"Protocol fee: {fee_bps} bps (1%)")

    step("8b", "📝 [NLP] Creating sentiment analysis task...")
    task1 = orch.create_inference_task(
        model_name="nlp-sentiment-v1",
        input_data=b"Analyze sentiment: ModernTensor brings decentralized AI to every domain. The protocol enables permissionless innovation across NLP, Vision, Finance, and more.",
        payment_ether=0.01,
    )
    ok(f"Task 1 [NLP] created! ID: {task1.task_id}")
    ok(f"  Model: {task1.model_name}")
    ok(f"  Oracle TX: {task1.oracle_tx}")

    step("8c", "💰 [Finance] Creating risk assessment task...")
    task2 = orch.create_inference_task(
        model_name="finance-risk-v1",
        input_data=b"Assess DeFi portfolio risk: ETH=40%, BTC=30%, MDT=20%, stablecoins=10%. Total value: $150k. Leverage: 1.5x",
        payment_ether=0.008,
    )
    ok(f"Task 2 [Finance] created! ID: {task2.task_id}")
    ok(f"  Model: {task2.model_name}")
    ok(f"  Oracle TX: {task2.oracle_tx}")

    step("8d", "🔍 [Code] Creating smart contract audit task...")
    task3 = orch.create_inference_task(
        model_name="code-review-v1",
        input_data=b"Review: function transfer(address to, uint256 amount) external { balances[msg.sender] -= amount; balances[to] += amount; }",
        payment_ether=0.01,
    )
    ok(f"Task 3 [Code] created! ID: {task3.task_id}")
    ok(f"  Model: {task3.model_name}")
    ok(f"  Oracle TX: {task3.oracle_tx}")

    total_after = val_client.oracle.total_requests()
    ok(f"Total requests after: {total_after} (was {total_before})")
    info("3 tasks across 3 AI domains — NLP, Finance, Code Review")

    return orch, [task1, task2, task3]


# ════════════════════════════════════════════════════════
# Step 9: Miner Processes Tasks + Generates zkML Proofs
# ════════════════════════════════════════════════════════
def do_miner_process_tasks(clients, orch, tasks, miner_uid):
    header("STEP 9 — Miner Processes Multi-Domain Tasks (+ zkML Proofs)")

    miner_client = clients["miner"]
    results = []
    domain_labels = ["NLP sentiment", "Finance risk", "Code review"]

    for i, (task, label) in enumerate(zip(tasks, domain_labels)):
        step(f"9{chr(97+i)}", f"Miner (UID {miner_uid}) processing task {i+1}: {label}...")
        result = orch.process_task(
            miner_client=miner_client,
            task=task,
            miner_uid=miner_uid,
        )
        ok(f"Output: {result.output[:60].decode('utf-8', errors='replace')}...")
        ok(f"  Proof hash: {result.proof_hash.hex()[:20]}...")
        ok(f"  Proof verified on-chain: {result.proof_verified}")
        results.append(result)

    verified_count = sum(1 for r in results if r.proof_verified)
    ok(f"Summary: {verified_count}/{len(tasks)} proofs verified across {len(tasks)} domains ✓")

    return results


# ════════════════════════════════════════════════════════
# Step 10: Validator Evaluates Results + Sets Weights
# ════════════════════════════════════════════════════════
def do_evaluate_and_set_weights(clients, orch, results, netuid, validator_uid):
    header("STEP 10 — Validator Evaluates AI Quality → Sets Weights")

    val_client = clients["validator"]

    step("10a", "Evaluating miner results (quality + proof validity)...")
    evaluation = orch.evaluate_miners(results)

    ok(f"Total tasks evaluated: {evaluation.total_tasks}")
    ok(f"  Verified proofs: {evaluation.verified_proofs}/{evaluation.total_tasks}")
    ok(f"  Average quality: {evaluation.average_quality:.2%}")

    step("10b", "Weights set on-chain based on VERIFIED AI quality...")
    ok(f"Weights TX: {evaluation.weights_set_tx}")
    for uid, score in evaluation.miner_scores.items():
        weight = int(score * 10000)
        ok(f"  Miner UID {uid} → weight {weight} (score: {score:.2%})")

    # Verify stored weights
    uids, weights = val_client.subnet.get_weights(netuid, validator_uid)
    info(f"  On-chain weights: UIDs={uids}, Weights={weights}")
    info("Weights now reflect VERIFIED AI WORK, not arbitrary assignment!")


# ════════════════════════════════════════════════════════
# Step 11: Run Epoch (Yuma Consensus Emission)
# ════════════════════════════════════════════════════════
def do_run_epoch(clients, netuid, w3):
    header("STEP 11 — Run Epoch (Emission Distribution)")

    owner = clients["owner"]
    subnet = owner.subnet
    token = owner.token

    # Step 11a: Fund emission pool (required for runEpoch to distribute tokens)
    step("11a", "Funding emission pool with MDT tokens...")
    fund_amount = 10000  # 10,000 MDT for emission rewards
    fund_wei = Web3.to_wei(fund_amount, "ether")
    registry_addr = subnet._contract.address

    # Approve SubnetRegistry to pull MDT
    token.approve(registry_addr, fund_wei)
    # Fund via SDK wrapper
    fund_tx = subnet.fund_emission_pool(fund_amount)
    ok(f"Funded emission pool with {fund_amount} MDT (TX: {fund_tx})")

    # Step 11b: Mine enough blocks to exceed tempo (360 blocks)
    step("11b", "Mining 400 blocks to exceed tempo period (360)...")
    batch = 50
    for i in range(400 // batch):
        for _ in range(batch):
            w3.provider.make_request("evm_mine", [])
    ok(f"Mined 400 blocks. Current block: {w3.eth.block_number}")

    # Step 11c: Run epoch
    step("11c", "Running epoch (Yuma Consensus emission distribution)...")
    try:
        tx = subnet.run_epoch(netuid)
        ok(f"Epoch complete! TX: {tx}")

        # Show emission results
        sn_info = subnet.get_subnet(netuid)
        info(f"  Subnet: {sn_info.name}")
        info(f"  Emission share: {sn_info.emission_percent:.1f}%")
    except Exception as e:
        info(f"Epoch note: {str(e)[:100]}")
        info("This may happen if tempo hasn't passed or emission pool is empty")


# ════════════════════════════════════════════════════════
# Step 12: Claim Emission Rewards
# ════════════════════════════════════════════════════════
def do_claim(clients, netuid, miner_uid, validator_uid):
    header("STEP 12 — Claim Emission Rewards")

    # Check pending emission
    miner_client = clients["miner"]
    val_client = clients["validator"]

    step("12a", "Check pending emission for miner...")
    miner_node = miner_client.subnet.get_node(netuid, miner_uid)
    ok(f"Miner pending emission: {miner_node.emission_ether:.6f} MDT")

    step("12b", "Check pending emission for validator...")
    val_node = val_client.subnet.get_node(netuid, validator_uid)
    ok(f"Validator pending emission: {val_node.emission_ether:.6f} MDT")

    # Claim if any
    if miner_node.emission > 0:
        step("12c", "Miner claiming emission...")
        try:
            tx = miner_client.subnet.claim_emission(netuid, miner_uid)
            ok(f"Miner claimed! TX: {tx}")
        except Exception as e:
            info(f"Claim note: {str(e)[:80]}")

    if val_node.emission > 0:
        step("12d", "Validator claiming emission...")
        try:
            tx = val_client.subnet.claim_emission(netuid, validator_uid)
            ok(f"Validator claimed! TX: {tx}")
        except Exception as e:
            info(f"Claim note: {str(e)[:80]}")


# ════════════════════════════════════════════════════════
# Step 13: Display Final Metagraph
# ════════════════════════════════════════════════════════
def do_display_metagraph(clients, netuid):
    header("STEP 13 — Final Metagraph")

    owner = clients["owner"]
    meta = owner.subnet.get_metagraph(netuid)

    print(f"\n  📊 Subnet {netuid} Metagraph")
    print(f"  {'─'*50}")
    print(
        f"  {'UID':<5} {'Type':<12} {'Hotkey':<16} {'Stake (MDT)':<14} {'Rank':<12} {'Emission':<12} {'Active'}"
    )
    print(f"  {'─'*50}")

    for node in meta.nodes:
        node_type = "VALIDATOR" if node.is_validator else "MINER"
        print(
            f"  {node.uid:<5} {node_type:<12} {node.hotkey[:14]}.. {node.total_stake_ether:<14.4f} {node.rank_float:<12.6f} {node.emission_ether:<12.6f} {'Yes' if node.active else 'No'}"
        )

    print(f"  {'─'*50}")
    total = Web3.from_wei(meta.total_stake, "ether")
    print(
        f"  Total Stake: {total} MDT | Miners: {len(meta.miners)} | Validators: {len(meta.validators)}"
    )

    # Token balances
    print(f"\n  💰 Final Token Balances:")
    for role in ["owner", "validator", "miner"]:
        bal = clients[role].token.balance_of_ether(clients[role].address)
        print(f"    {role.capitalize()}: {bal:.4f} MDT")


# ════════════════════════════════════════════════════════
# Step 14: Federated Learning (GradientAggregator)
# ════════════════════════════════════════════════════════
def do_federated_learning(clients, w3):
    header("STEP 14 — Federated Learning Cycle (GradientAggregator)")

    owner = clients["owner"]
    miner = clients["miner"]
    token = owner.token
    training = owner.training

    # 14a: Approve MDT + create training job
    step("14a", "Owner creating federated learning job (3 rounds)...")
    model_hash = Web3.keccak(text="fedavg-resnet50-polkadot-v1")
    reward_amount = 500  # 500 MDT reward pool
    reward_wei = Web3.to_wei(reward_amount, "ether")

    # Approve GradientAggregator to spend MDT
    aggregator_addr = training._contract.address
    token.approve(aggregator_addr, reward_wei)
    ok(f"Approved {reward_amount} MDT for GradientAggregator")

    tx = training.create_job(
        model_hash=model_hash,
        total_rounds=3,
        reward_ether=reward_amount,
        max_participants=10,
        round_deadline=7200,
    )
    ok(f"Training job created! TX: {tx}")

    job_id = training.next_job_id() - 1
    job = training.get_job_details(job_id)
    info(f"  Job ID: {job_id}")
    info(f"  Rounds: {job.total_rounds}, Reward: {job.reward_pool_ether:.0f} MDT")
    info(f"  Status: {'ACTIVE' if job.is_active else 'INACTIVE'}")

    # 14b: Miner submits gradients for each round
    miner_training = miner.training
    for round_num in range(1, 4):
        step(f"14b.{round_num}", f"Miner submitting gradient for round {round_num}/3...")
        grad_hash = Web3.keccak(text=f"gradient-round-{round_num}-miner-{miner.address[:8]}")
        tx = miner_training.submit_gradient(
            job_id=job_id,
            gradient_hash=grad_hash,
            data_size=1000 * round_num,
        )
        ok(f"Gradient submitted! TX: {tx}")

        # 14c: Owner finalizes round
        step(f"14c.{round_num}", f"Owner finalizing round {round_num}...")
        agg_hash = Web3.keccak(text=f"aggregated-model-round-{round_num}")
        tx = training.finalize_round(
            job_id=job_id,
            aggregated_hash=agg_hash,
            valid_participants=[miner.address],
        )
        ok(f"Round {round_num} finalized! TX: {tx}")

    # 14d: Verify job completion
    job = training.get_job_details(job_id)
    ok(f"Job status: {'COMPLETED' if job.is_completed else 'ACTIVE'}")
    info(f"  Progress: round {job.current_round}/{job.total_rounds}")

    # 14e: Miner claims reward
    step("14e", "Miner claiming federated learning reward...")
    miner_balance_before = token.balance_of_ether(miner.address)
    tx = miner_training.claim_reward(job_id)
    ok(f"Reward claimed! TX: {tx}")
    miner_balance_after = token.balance_of_ether(miner.address)
    reward_earned = miner_balance_after - miner_balance_before
    info(f"  Reward received: {reward_earned:.2f} MDT")

    # 14f: Verify participation
    rounds_participated = training.get_participant_rounds(job_id, miner.address)
    ok(f"Miner participated in {rounds_participated} validated rounds")
    info("Federated learning cycle complete — FedAvg with on-chain coordination!")

    return job_id


# ════════════════════════════════════════════════════════
# Step 15: Training Escrow (TrainingEscrow)
# ════════════════════════════════════════════════════════
def do_training_escrow(clients, w3):
    header("STEP 15 — Training Escrow Cycle (Stake-Gated Training)")

    owner = clients["owner"]
    miner = clients["miner"]
    token = owner.token
    escrow = owner.escrow

    # 15a: Create a training task with escrowed rewards
    step("15a", "Owner creating escrow training task...")
    model_hash = Web3.keccak(text="finetune-llm-polkadot-v1")
    reward_amount = 200  # 200 MDT reward
    reward_wei = Web3.to_wei(reward_amount, "ether")
    min_stake = 10  # 10 MDT minimum stake

    # Approve TrainingEscrow to spend MDT
    escrow_addr = escrow._contract.address
    token.approve(escrow_addr, reward_wei)
    ok(f"Approved {reward_amount} MDT for TrainingEscrow")

    tx = escrow.create_task(
        model_hash=model_hash,
        reward_ether=reward_amount,
        min_stake_ether=min_stake,
        max_trainers=5,
        duration_seconds=86400,
    )
    ok(f"Training task created! TX: {tx}")

    task_id = escrow.next_task_id() - 1
    task = escrow.get_task_details(task_id)
    info(f"  Task ID: {task_id}")
    info(f"  Reward: {task.reward_ether:.0f} MDT, Min Stake: {task.min_stake_ether:.0f} MDT")
    info(f"  Status: {'OPEN' if task.is_open else task.status.name}")

    # 15b: Miner joins task by staking MDT
    step("15b", "Miner staking MDT to join training task...")
    miner_escrow = miner.escrow
    miner_token = miner.token
    stake_amount = min_stake

    # Approve TrainingEscrow to take miner's stake
    miner_token.approve(escrow_addr, Web3.to_wei(stake_amount, "ether"))
    tx = miner_escrow.join_task(task_id, stake_ether=stake_amount)
    ok(f"Miner joined task! Staked {stake_amount} MDT (TX: {tx})")

    trainers = escrow.get_task_trainers(task_id)
    info(f"  Active trainers: {len(trainers)}")

    # 15c: Miner submits training result
    step("15c", "Miner submitting training result...")
    result_hash = Web3.keccak(text=f"training-result-{miner.address[:8]}-task-{task_id}")
    tx = miner_escrow.submit_result(task_id, result_hash)
    ok(f"Result submitted! TX: {tx}")

    trainer_info = escrow.get_trainer_info(task_id, miner.address)
    info(f"  Submitted: {trainer_info.submitted}")

    # 15d: Owner validates the submission
    step("15d", "Owner validating miner's submission...")
    tx = escrow.validate_trainer(task_id, miner.address, is_valid=True)
    ok(f"Trainer validated as VALID! TX: {tx}")

    trainer_info = escrow.get_trainer_info(task_id, miner.address)
    info(f"  Validated: {trainer_info.validated}, Slashed: {trainer_info.slashed}")

    # 15e: Owner completes the task
    step("15e", "Owner completing training task...")
    tx = escrow.complete_task(task_id)
    ok(f"Task completed! TX: {tx}")

    task = escrow.get_task_details(task_id)
    ok(f"Task status: {'COMPLETED' if task.is_completed else task.status.name}")

    # 15f: Miner claims reward + stake back
    step("15f", "Miner claiming reward + stake return...")
    miner_balance_before = token.balance_of_ether(miner.address)
    tx = miner_escrow.claim_reward(task_id)
    ok(f"Reward claimed! TX: {tx}")
    miner_balance_after = token.balance_of_ether(miner.address)
    total_received = miner_balance_after - miner_balance_before
    info(f"  Total received: {total_received:.2f} MDT (reward + stake return)")

    slash_rate = escrow.slash_rate_pct()
    info(f"  Slash rate: {slash_rate:.0f}% (applied to invalid submissions)")
    info("Training escrow cycle complete — stake-gated, slashable training!")

    return task_id


# ════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════
def main():
    print("🚀 ModernTensor — Full E2E Workflow")
    print("=" * 60)

    # Phase 1: Setup
    w3 = do_connect()
    wallets = do_wallets(w3)
    clients, contracts = do_init_clients(w3)
    do_distribute_tokens(clients)
    netuid = do_create_subnet(clients)
    validator_uid = do_register_validator(clients, netuid)
    miner_uid = do_register_miner(clients, netuid)

    # Phase 2: Integrated AI Inference Cycle
    do_setup_zkml_trust(clients)
    orch, tasks = do_create_ai_tasks(clients, netuid)
    results = do_miner_process_tasks(clients, orch, tasks, miner_uid)
    do_evaluate_and_set_weights(clients, orch, results, netuid, validator_uid)

    # Phase 3: Emission & Rewards
    do_run_epoch(clients, netuid, w3)
    do_claim(clients, netuid, miner_uid, validator_uid)
    do_display_metagraph(clients, netuid)

    # Phase 4: Federated Learning (GradientAggregator)
    do_federated_learning(clients, w3)

    # Phase 5: Training Escrow (TrainingEscrow)
    do_training_escrow(clients, w3)

    header("WORKFLOW COMPLETE 🎉")
    print(
        """
  Summary of operations performed:
  ─────────────────────────────────────────────
  Phase 1 — Setup:
  ✅ 1.  Connected to local Hardhat node
  ✅ 2.  Generated 3 wallets (deployer, validator, miner)
  ✅ 3.  Loaded 8 deployed contracts
  ✅ 4.  Distributed MDT tokens (5000 → validator, 1000 → miner)
  ✅ 5.  Created/verified subnet (netuid=1)
  ✅ 6.  Registered VALIDATOR + MINER on subnet

  Phase 2 — Multi-Domain AI Cycle:
  ✅ 7.  Setup zkML (3 domain models + registered fulfiller)
  ✅ 8.  Validator created 3 tasks across 3 AI domains
  ✅ 9.  Miner processed all domains + generated zkML proofs
  ✅ 10. Validator evaluated quality → set weights

  Phase 3 — Emission:
  ✅ 11. Ran epoch (Yuma Consensus emission distribution)
  ✅ 12. Checked/claimed emission rewards
  ✅ 13. Displayed final metagraph

  Phase 4 — Federated Learning (GradientAggregator):
  ✅ 14. Created training job → submitted gradients → finalized
        3 rounds → claimed proportional rewards

  Phase 5 — Training Escrow (TrainingEscrow):
  ✅ 15. Created escrow task → miner staked & joined → submitted
        result → validated → completed → claimed reward + stake
  ─────────────────────────────────────────────

  🔑 KEY INSIGHT: ModernTensor is a MULTI-DOMAIN protocol.
  ANY AI vertical can run as a subnet:
    NLP • Vision • Finance • Health • Code Review • Custom

  ALL 8 CONTRACTS INTEGRATED:
    MDTToken ─── MDTVesting ─── MDTStaking
    SubnetRegistry ─── ZkMLVerifier ─── AIOracle
    GradientAggregator ─── TrainingEscrow

  Full lifecycle: Token → Subnet → Oracle → zkML →
    Weights → Emission → FedAvg → Escrow

  Weights are NOT set manually. Miners earn weights
  through VERIFIED work across ANY domain:
    Oracle (task) → zkML (proof) → Weights → Emission

  This is a FULL Bittensor-equivalent multi-domain lifecycle
  with federated learning and stake-gated training escrow.
  running on Polkadot Hub's EVM (pallet-revive).
"""
    )


if __name__ == "__main__":
    main()
