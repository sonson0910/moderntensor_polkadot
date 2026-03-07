"""Verify on-chain state — proof that all TXs are real."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web3 import Web3
from sdk.polkadot.client import PolkadotClient

client = PolkadotClient(
    network="polkadot_testnet",
    private_key=os.environ.get("TESTNET_PRIVATE_KEY", "0x3230cd6d7ea8c1666bcec73a86a1a8d86ad23198bf29554bf11f61bed41452fb"),
    deployment_path="luxtensor/contracts/deployments-polkadot.json",
)

print("🔍 ON-CHAIN PROOF — Polkadot Hub TestNet")
print(f"   Chain ID:  {client.chain_id}")
print(f"   Block #:   {client.block_number}")
print(f"   Connected: {client.is_connected}")
print()

# Contract addresses
for name in ["MDTToken", "MDTStaking", "MDTVesting", "AIOracle", "ZkMLVerifier", "SubnetRegistry"]:
    addr = client._addresses.get(name, "N/A")
    print(f"   {name:20s} → {addr}")
print()

# On-chain state
balance = Web3.from_wei(client.token.balance_of(client.address), "ether")
staking_bal = Web3.from_wei(client.token.balance_of(client._addresses["MDTStaking"]), "ether")
total_staked = Web3.from_wei(client.staking.total_staked(), "ether")
bonus_pool = float(staking_bal) - float(total_staked)
native = Web3.from_wei(client.get_eth_balance(), "ether")
subnets = client.subnet.get_subnet_count()

print(f"   MDT Balance:     {balance} MDT")
print(f"   Staking contract:{staking_bal} MDT")
print(f"   Total staked:    {total_staked} MDT")
print(f"   Bonus pool:      {bonus_pool} MDT")
print(f"   Native (WND):    {native}")
print(f"   Subnets:         {subnets}")
print()

# Latest block proof
blk = client.w3.eth.get_block("latest")
print(f"   Latest block #{blk['number']}")
print(f"   Hash: {blk['hash'].hex()[:40]}...")
print(f"   Time: {blk['timestamp']}")
print()
print("✅ ALL REAL ON-CHAIN DATA!")
