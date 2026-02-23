"""
Quick test: verify SubnetRegistry v2 (consensus security) on Polkadot Hub TestNet.
"""
import os, sys, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sdk.polkadot.client import PolkadotClient
from sdk.polkadot.subnet import NodeType
from web3 import Web3

PRIVATE_KEY = "0x3230cd6d7ea8c1666bcec73a86a1a8d86ad23198bf29554bf11f61bed41452fb"
DEPLOYMENT_PATH = "luxtensor/contracts/deployments-polkadot.json"

client = PolkadotClient(
    network="polkadot_testnet",
    private_key=PRIVATE_KEY,
    deployment_path=DEPLOYMENT_PATH,
)
subnet = client.subnet
token = client.token
w3 = client.w3

passed = 0
failed = 0

def step(name, func):
    global passed, failed
    try:
        result = func()
        print(f"  ✅ {name}: {result}")
        passed += 1
        return result
    except Exception as e:
        err = str(e)[:200]
        print(f"  ❌ {name}: {err}")
        failed += 1
        return None

print("=" * 60)
print("  SubnetRegistry v2 — Consensus Security Verification")
print("=" * 60)
print(f"  Deployer: {client.address}")
print(f"  Balance:  {w3.from_wei(client.get_eth_balance(), 'ether')} PAS")
print()

# ── 1. Basic reads ──────────────────────────────────────────
print("━" * 60)
print("TEST 1: Basic Read Operations")
print("━" * 60)

count = step("Subnet count", lambda: subnet.get_subnet_count())
next_id = step("Next netuid", lambda: subnet.next_netuid())

# ── 2. Create subnet ────────────────────────────────────────
print()
print("━" * 60)
print("TEST 2: Create Subnet + Self-Vote Protection")
print("━" * 60)

registry_addr = subnet._contract.address
step("Approve 100 MDT for SubnetRegistry",
     lambda: token.approve(registry_addr, Web3.to_wei(100, "ether")))

result = step("Create subnet 'SecureAI-Test'",
              lambda: subnet.create_subnet("SecureAI-Test", max_nodes=128, tempo=100))
if result:
    tx_hash, netuid = result
    print(f"  → Assigned netuid: {netuid}")

    info = step(f"Get subnet #{netuid}",
                lambda: f"name={subnet.get_subnet(netuid).name}, active={subnet.get_subnet(netuid).active}")

    # Register as miner
    step(f"Register miner in subnet #{netuid}",
         lambda: subnet.register_miner(netuid))

    step(f"Is registered?",
         lambda: f"registered={subnet.is_registered(netuid)}")

    # Get node info (should include trust)
    uid = step(f"Get UID", lambda: subnet.get_uid(netuid))
    if uid is not None:
        node = step(f"Get node #{uid} (with trust)",
                    lambda: f"trust={subnet.get_node(netuid, uid).trust_float:.2f}, type={'MINER' if subnet.get_node(netuid, uid).is_miner else 'VALIDATOR'}")

    # Self-vote protection test: try to also register as validator (should FAIL)
    print()
    print("  [SECURITY TEST] Self-vote protection:")
    try:
        subnet.register_validator(netuid, hotkey="0x0000000000000000000000000000000000000002")
        print("  ❌ Self-vote protection FAILED — should have reverted!")
        failed += 1
    except Exception as e:
        if "Self-vote" in str(e) or "opposite type" in str(e) or "execution reverted" in str(e):
            print(f"  ✅ Self-vote protection WORKS — correctly rejected!")
            passed += 1
        else:
            print(f"  ❌ Unexpected error: {str(e)[:200]}")
            failed += 1

# ── 3. Slashing test ────────────────────────────────────────
print()
print("━" * 60)
print("TEST 3: Slashing Mechanism")
print("━" * 60)

if result and uid is not None:
    step(f"Slash node #{uid} (5%)",
         lambda: subnet.slash_node(netuid, uid, 500, "Test slash"))

# ── 4. Trust score ────────────────────────────────────────
print()
print("━" * 60)
print("TEST 4: Trust Score Query")
print("━" * 60)

if result and uid is not None:
    trust = step(f"Get trust score for node #{uid}",
                 lambda: f"trust={subnet.get_trust(netuid, uid):.4f}")

# ── 5. Set weights (legacy, backward compat) ─────────────
print()
print("━" * 60)
print("TEST 5: Legacy setWeights (backward compat)")
print("━" * 60)

# For this we'd need a validator, but since we registered as miner
# we can't set weights. Test that it correctly rejects.
if result:
    try:
        subnet.set_weights(netuid, [0], [100])
        print("  ❌ Should have rejected — we are a miner, not validator!")
        failed += 1
    except Exception as e:
        if "Not a validator" in str(e) or "execution reverted" in str(e):
            print("  ✅ Role enforcement WORKS — miner cannot set weights")
            passed += 1
        else:
            print(f"  ❌ Unexpected: {str(e)[:200]}")
            failed += 1

# ── Summary ──────────────────────────────────────────────
print()
print("=" * 60)
print(f"  RESULTS: {passed}/{passed+failed} passed, {failed} failed")
print("=" * 60)

if failed == 0:
    print("  🎉 ALL SECURITY TESTS PASSED!")
else:
    print(f"  ⚠️  {failed} test(s) failed")
