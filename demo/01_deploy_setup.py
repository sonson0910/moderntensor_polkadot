#!/usr/bin/env python3
"""
ModernTensor Demo — Step 1: Deploy & Setup

Deploys all 8 smart contracts to a local Hardhat node and performs
initial setup (TGE, zkML dev mode, model approval, subnet creation).

Prerequisites:
  cd luxtensor/contracts && npx hardhat node

Usage:
  python demo/01_deploy_setup.py
  NETWORK=polkadot_testnet python demo/01_deploy_setup.py
"""

import subprocess
import sys
import os
import json
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from demo.config import (
    get_network,
    get_private_key,
    banner,
    step_log,
    ok,
    info,
    fail,
    warn,
    PROJECT_ROOT,
    SUBNET_NAME,
    SUBNET_MAX_NODES,
    SUBNET_MIN_STAKE,
    SUBNET_TEMPO,
    EMISSION_FUND,
    AI_MODELS,
)
from web3 import Web3


def deploy_contracts(network_name="local"):
    """Deploy contracts via Hardhat."""
    banner("STEP 1/3 — Deploy Smart Contracts")

    contracts_dir = PROJECT_ROOT / "luxtensor" / "contracts"
    net = get_network(network_name)

    deploy_file = Path(net["deployment"])
    if deploy_file.exists():
        with open(deploy_file) as f:
            data = json.load(f)
        contracts = data.get("contracts", data)
        if len(contracts) >= 8:
            ok(f"Contracts already deployed ({len(contracts)} found)")
            for name, addr in contracts.items():
                info(f"  {name}: {addr}")
            return contracts

    step_log("1a", "Compiling contracts...")
    result = subprocess.run(
        ["npx", "hardhat", "compile"],
        cwd=str(contracts_dir),
        capture_output=True,
        text=True,
        shell=True,
    )
    if result.returncode != 0:
        fail(f"Compilation failed:\n{result.stderr}")
    ok("Contracts compiled")

    step_log("1b", f"Deploying to {net['label']}...")
    hardhat_network = "luxtensor_local" if network_name == "local" else network_name
    deploy_script = "scripts/deploy-polkadot.js"

    result = subprocess.run(
        ["npx", "hardhat", "run", deploy_script, "--network", hardhat_network],
        cwd=str(contracts_dir),
        capture_output=True,
        text=True,
        shell=True,
    )
    if result.returncode != 0:
        fail(f"Deployment failed:\n{result.stderr}")

    ok("Deployment complete!")
    print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)

    # Load deployed addresses
    with open(deploy_file) as f:
        data = json.load(f)
    contracts = data.get("contracts", data)
    for name, addr in contracts.items():
        info(f"  {name}: {addr}")

    return contracts


def setup_initial_state(network_name="local"):
    """Initialize: TGE, zkML, Oracle models, subnet, emission pool."""
    banner("STEP 2/3 — Initialize Protocol State")

    from sdk.polkadot.client import PolkadotClient

    net = get_network(network_name)
    owner_key = get_private_key("deployer")

    client = PolkadotClient(
        rpc_url=net["rpc_url"],
        private_key=owner_key,
        deployment_path=net["deployment"],
    )

    ok(f"Connected: {net['label']} (chain {client.chain_id})")
    ok(f"Owner: {client.address}")

    # --- TGE Check ---
    step_log("2a", "Checking TGE (Token Generation Event)...")
    token = client.token
    balance = token.balance_of_ether(client.address)
    ok(f"Owner MDT balance: {balance:,.2f} MDT")

    if balance < 1000:
        warn("Low balance — attempting TGE mint...")
        try:
            tx = token.execute_tge(0, client.address)  # CAT_EMISSION_REWARDS
            ok(f"TGE executed: {tx}")
        except Exception as e:
            info(f"TGE may already be executed: {e}")

    # --- zkML Dev Mode ---
    step_log("2b", "Enabling zkML dev mode...")
    zkml = client.zkml
    if not zkml.dev_mode_enabled():
        tx = zkml.set_dev_mode(True)
        ok(f"Dev mode enabled: {tx}")
    else:
        ok("Dev mode already enabled")

    # --- Trust AI Model Images ---
    step_log("2c", "Trusting AI model images...")
    for model_name in AI_MODELS:
        image_id = Web3.keccak(text=model_name)
        if not zkml.is_image_trusted(image_id):
            tx = zkml.trust_image(image_id)
            ok(f"Trusted '{model_name}': {tx}")
        else:
            ok(f"Already trusted: {model_name}")

    # --- Approve Models in Oracle ---
    step_log("2d", "Approving models in AI Oracle...")
    oracle = client.oracle
    for model_name in AI_MODELS:
        model_hash = Web3.keccak(text=model_name)
        if not oracle.is_model_approved(model_hash):
            tx = oracle.approve_model(model_hash)
            ok(f"Oracle approved '{model_name}': {tx}")
        else:
            ok(f"Already approved: {model_name}")

    return client


def setup_subnet(client, network_name="local"):
    """Create subnet + fund emission pool."""
    banner("STEP 3/3 — Create Subnet & Fund Emission Pool")

    subnet = client.subnet
    token = client.token

    # Check existing subnets
    step_log("3a", "Checking subnets...")
    count = subnet.get_subnet_count()
    ok(f"Existing subnets: {count}")

    netuid = 1
    if count > 0:
        s = subnet.get_subnet(1)
        ok(f"Subnet 1 exists: '{s.name}' (tempo={s.tempo}, max={s.max_nodes})")
    else:
        step_log("3b", f"Creating subnet '{SUBNET_NAME}'...")
        registry_addr = client._get_contract("SubnetRegistry").address
        cost = Web3.to_wei(100, "ether")  # 100 MDT creation cost
        token.approve(registry_addr, cost)
        tx, netuid = subnet.create_subnet(
            name=SUBNET_NAME,
            max_nodes=SUBNET_MAX_NODES,
            min_stake_ether=SUBNET_MIN_STAKE,
            tempo=SUBNET_TEMPO,
        )
        ok(f"Subnet created! netuid={netuid}, TX: {tx}")

    # Fund emission pool
    step_log("3c", f"Funding emission pool with {EMISSION_FUND} MDT...")
    registry_addr = client._get_contract("SubnetRegistry").address
    token.approve(registry_addr, Web3.to_wei(EMISSION_FUND, "ether"))
    try:
        tx = subnet.fund_emission_pool(EMISSION_FUND)
        ok(f"Emission pool funded: {tx}")
    except Exception as e:
        info(f"Emission pool note: {str(e)[:100]}")

    return netuid


def main():
    print("\n🚀 ModernTensor — Deploy & Setup")
    print("   Polkadot Solidity Hackathon 2026 — Track 1: EVM\n")

    network_name = os.environ.get("NETWORK", "local")
    net = get_network(network_name)
    info(f"Target: {net['label']} ({net['rpc_url']})")

    # Step 1: Deploy
    contracts = deploy_contracts(network_name)

    # Step 2: Initialize
    client = setup_initial_state(network_name)

    # Step 3: Subnet + Emission
    netuid = setup_subnet(client, network_name)

    banner("DEPLOY & SETUP COMPLETE ✅")
    print(
        f"""
  Network:     {net['label']}
  Contracts:   {len(contracts)} deployed
  Subnet:      netuid={netuid} ({SUBNET_NAME})
  Emission:    {EMISSION_FUND} MDT funded
  zkML:        Dev mode ON, {len(AI_MODELS)} models trusted
  Oracle:      {len(AI_MODELS)} models approved

  Next steps:
    python demo/02_register_keys.py    # Register wallet keys
    python demo/03_faucet.py           # Get tokens (faucet)
    python demo/04_register_subnet.py  # Register miner + validator
    python demo/05_run_miner.py        # Start miner
    python demo/06_run_validator.py    # Start validator
    python demo/07_run_demo.py         # Run complete demo
"""
    )


if __name__ == "__main__":
    main()
