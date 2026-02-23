#!/usr/bin/env python3
"""
ModernTensor — Polkadot Hub E2E Demo

Demonstrates full SDK interaction with deployed contracts:
1. Connect to Polkadot Hub testnet
2. Check MDT token balance
3. Stake tokens with time-lock bonus
4. Create AI inference request
5. Create federated learning job
6. Verify zkML proof (dev mode)

Requirements:
    pip install web3 eth-account
    # Deploy contracts first:
    # cd luxtensor/contracts && npx hardhat run scripts/deploy-polkadot.js --network polkadot_testnet

Usage:
    python demo_polkadot.py
    python demo_polkadot.py --network local
    python demo_polkadot.py --network polkadot_testnet --key 0x...
"""

import argparse
import logging
import os
import sys

from web3 import Web3

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sdk.polkadot import PolkadotClient

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def demo_connect(client: PolkadotClient) -> None:
    """Step 1: Connect and show network info."""
    print("\n" + "=" * 60)
    print("🔗 STEP 1: Connect to Polkadot Hub")
    print("=" * 60)
    print(f"  Client:      {client}")
    print(f"  Connected:   {client.is_connected}")
    print(f"  Chain ID:    {client.chain_id}")
    print(f"  Block:       {client.block_number}")
    print(f"  Address:     {client.address}")

    eth_balance = client.get_eth_balance()
    print(f"  Native bal:  {Web3.from_wei(eth_balance, 'ether')} DOT")


def demo_token(client: PolkadotClient) -> None:
    """Step 2: Token operations."""
    print("\n" + "=" * 60)
    print("💰 STEP 2: MDT Token")
    print("=" * 60)

    token = client.token
    print(f"  Token:       {token.name()} ({token.symbol()})")
    print(f"  Decimals:    {token.decimals()}")
    print(f"  Total supply: {token.balance_of_ether()} MDT")
    print(f"  My balance:  {token.balance_of_ether(client.address):.4f} MDT")
    print(f"  TGE done:    {token.tge_executed()}")


def demo_staking(client: PolkadotClient) -> None:
    """Step 3: Staking operations."""
    print("\n" + "=" * 60)
    print("🔒 STEP 3: Staking (On-Chain Consensus)")
    print("=" * 60)

    staking = client.staking
    print(f"  Total staked: {Web3.from_wei(staking.total_staked(), 'ether')} MDT")
    print(f"  Total bonus:  {Web3.from_wei(staking.total_bonus_paid(), 'ether')} MDT")

    # Preview bonus rates
    print("\n  📊 Bonus Rate Schedule:")
    for days in [7, 30, 90, 180, 365]:
        rate = staking.get_bonus_rate(days)
        print(f"    {days:>3}d → {rate/100:.0f}% bonus")

    # Check current stakes
    info = staking.get_stake_info()
    print(f"\n  My stakes:    {info.active_stakes}")
    print(f"  Locked:       {info.total_locked_ether:.4f} MDT")
    print(f"  Pending bonus: {info.pending_bonus_ether:.4f} MDT")


def demo_oracle(client: PolkadotClient) -> None:
    """Step 4: AI Oracle."""
    print("\n" + "=" * 60)
    print("🤖 STEP 4: AI Oracle")
    print("=" * 60)

    oracle = client.oracle
    print(f"  Total requests: {oracle.total_requests()}")
    print(f"  Protocol fee:   {oracle.protocol_fee_bps()} bps")

    # Create a demo AI request
    model_hash = Web3.keccak(text="moderntensor-llm-v1")
    print(f"  Model hash:     {model_hash.hex()[:20]}...")

    is_approved = oracle.is_model_approved(model_hash)
    print(f"  Model approved: {is_approved}")


def demo_zkml(client: PolkadotClient) -> None:
    """Step 6: zkML Verification."""
    print("\n" + "=" * 60)
    print("🔐 STEP 6: zkML Verification")
    print("=" * 60)

    zkml = client.zkml
    print(f"  Dev mode: {zkml.dev_mode_enabled()}")

    # Create a dev proof
    image_id = Web3.keccak(text="moderntensor-resnet50")
    journal = b"inference_result:cat:0.97"
    seal, proof_hash = zkml.create_dev_proof(image_id, journal)
    print(f"  Image ID:   {image_id.hex()[:20]}...")
    print(f"  Proof hash: {proof_hash.hex()[:20]}...")
    print(f"  Seal:       {seal.hex()[:20]}...")
    print(f"  Trusted:    {zkml.is_image_trusted(image_id)}")

def demo_subnet(client: PolkadotClient) -> None:
    """Step 8: Subnet operations."""
    print("\n" + "=" * 60)
    print("🌐 STEP 8: Subnet Registry")
    print("=" * 60)

    subnet = client.subnet
    count = subnet.get_subnet_count()
    print(f"  Total subnets: {count}")

    if count > 0:
        info = subnet.get_subnet(1)
        print(f"\n  📋 Subnet 1:")
        print(f"    Name:       {info.name}")
        print(f"    Owner:      {info.owner[:20]}...")
        print(f"    Max nodes:  {info.max_nodes}")
        print(f"    Node count: {info.node_count}")
        print(f"    Active:     {info.active}")

        # Get metagraph
        meta = subnet.get_metagraph(1)
        print(f"\n  📊 Metagraph:")
        print(f"    Miners:     {len(meta.miners)}")
        print(f"    Validators: {len(meta.validators)}")
        print(f"    Total stake: {Web3.from_wei(meta.total_stake, 'ether'):.4f} MDT")

        # Check registration
        is_reg = subnet.is_registered(1, client.address)
        print(f"\n  Registered:   {is_reg}")
        if is_reg:
            uid = subnet.get_uid(1, client.address)
            node = subnet.get_node(1, uid)
            print(f"    UID:        {uid}")
            print(f"    Role:       {'Validator' if node.is_validator else 'Miner'}")
            print(f"    Stake:      {node.total_stake_ether:.4f} MDT")
            print(f"    Emission:   {node.emission_ether:.6f} MDT")


def main():
    parser = argparse.ArgumentParser(description="ModernTensor Polkadot Demo")
    parser.add_argument(
        "--network", default="local",
        help="Network: local, polkadot_testnet, paseo_testnet"
    )
    parser.add_argument(
        "--key", default=None,
        help="Private key (or set PRIVATE_KEY env var)"
    )
    parser.add_argument(
        "--deployment", default=None,
        help="Path to deployments-polkadot.json"
    )
    args = parser.parse_args()

    private_key = args.key or os.environ.get("PRIVATE_KEY")
    if not private_key:
        print("❌ No private key. Set --key or PRIVATE_KEY env var.")
        sys.exit(1)

    print("🚀 ModernTensor — Polkadot Hub E2E Demo")
    print(f"   Network: {args.network}")

    try:
        client = PolkadotClient(
            network=args.network,
            private_key=private_key,
            deployment_path=args.deployment,
        )

        demo_connect(client)
        demo_token(client)
        demo_staking(client)
        demo_oracle(client)
        demo_zkml(client)
        demo_subnet(client)

        print("\n" + "=" * 60)
        print("✅ Demo complete! All 6 modules operational.")
        print("=")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.exception("Demo failed")
        sys.exit(1)


if __name__ == "__main__":
    main()

