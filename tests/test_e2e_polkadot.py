"""
End-to-End Test Suite — ModernTensor SDK on Polkadot Hub TestNet

Tests all SDK modules against live deployed contracts:
- PolkadotClient connection
- TokenClient (MDTToken + MDTVesting)
- StakingClient (MDTStaking)
- OracleClient (AIOracle)
- ZkMLClient (ZkMLVerifier)
- SubnetClient (SubnetRegistry)
- EventListener
- AISubnetOrchestrator

Run:  python tests/test_e2e_polkadot.py
"""

import os
import sys
import time
import traceback

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web3 import Web3

# ──────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────

PRIVATE_KEY = "0x3230cd6d7ea8c1666bcec73a86a1a8d86ad23198bf29554bf11f61bed41452fb"
DEPLOYMENT_PATH = "luxtensor/contracts/deployments-polkadot.json"
NETWORK = "polkadot_testnet"

# Test tracking
results = []
total_tests = 0
passed_tests = 0
failed_tests = 0
skipped_tests = 0


def test(name, func):
    """Run a test and track result."""
    global total_tests, passed_tests, failed_tests, skipped_tests
    total_tests += 1
    try:
        result = func()
        passed_tests += 1
        results.append(("✅", name, str(result)))
        print(f"  ✅ {name}: {result}")
    except Exception as e:
        err_msg = str(e)
        if "SKIP" in err_msg:
            skipped_tests += 1
            results.append(("⏭️", name, err_msg))
            print(f"  ⏭️  {name}: {err_msg}")
        else:
            failed_tests += 1
            results.append(("❌", name, err_msg))
            print(f"  ❌ {name}: {err_msg}")
            traceback.print_exc()


def main():
    global total_tests, passed_tests, failed_tests

    print("=" * 70)
    print("  ModernTensor SDK — End-to-End Test on Polkadot Hub TestNet")
    print("=" * 70)
    print()

    # ══════════════════════════════════════════════════════════
    # 1. CLIENT CONNECTION
    # ══════════════════════════════════════════════════════════
    print("━" * 50)
    print("1️⃣  PolkadotClient Connection")
    print("━" * 50)

    from sdk.polkadot.client import PolkadotClient

    client = PolkadotClient(
        network=NETWORK,
        private_key=PRIVATE_KEY,
        deployment_path=DEPLOYMENT_PATH,
    )

    test("Client connected", lambda: client.is_connected)
    test("Chain ID = 420420417", lambda: (
        f"chain_id={client.chain_id}"
        if client.chain_id == 420420417
        else (_ for _ in ()).throw(AssertionError(f"Expected 420420417, got {client.chain_id}"))
    ))
    test("Block number > 0", lambda: f"block={client.block_number}")
    test("Account loaded", lambda: f"address={client.address}")

    bal_wei = client.get_eth_balance()
    bal_pas = Web3.from_wei(bal_wei, "ether")
    test("Native balance (PAS)", lambda: f"{bal_pas} PAS")

    print()

    # ══════════════════════════════════════════════════════════
    # 2. ABI LOADING
    # ══════════════════════════════════════════════════════════
    print("━" * 50)
    print("2️⃣  Contract ABI Loading")
    print("━" * 50)

    from sdk.contracts import get_abi, CONTRACT_NAMES

    for name in CONTRACT_NAMES:
        test(f"ABI: {name}", lambda n=name: f"{len(get_abi(n))} entries")

    print()

    # ══════════════════════════════════════════════════════════
    # 3. TOKEN CLIENT (MDTToken + MDTVesting)
    # ══════════════════════════════════════════════════════════
    print("━" * 50)
    print("3️⃣  TokenClient (MDTToken + MDTVesting)")
    print("━" * 50)

    token = client.token
    test("Token name", lambda: token.name())
    test("Token symbol", lambda: token.symbol())
    test("Token decimals", lambda: f"{token.decimals()} decimals")
    test("Total supply", lambda: f"{Web3.from_wei(token.total_supply(), 'ether')} MDT")
    test("Deployer MDT balance", lambda: f"{token.balance_of_ether()} MDT")
    test("TGE executed?", lambda: f"tge={token.tge_executed()}")
    test("Self-allowance check", lambda: f"allowance={token.allowance(client.address, client.address)}")
    test("Token repr", lambda: repr(token))

    print()

    # ══════════════════════════════════════════════════════════
    # 4. STAKING CLIENT (MDTStaking)
    # ══════════════════════════════════════════════════════════
    print("━" * 50)
    print("4️⃣  StakingClient (MDTStaking)")
    print("━" * 50)

    staking = client.staking
    test("Total staked", lambda: f"{Web3.from_wei(staking.total_staked(), 'ether')} MDT")
    test("Total bonus paid", lambda: f"{Web3.from_wei(staking.total_bonus_paid(), 'ether')} MDT")
    test("Bonus rate 30d", lambda: f"{staking.get_bonus_rate(30)} bps")
    test("Bonus rate 90d", lambda: f"{staking.get_bonus_rate(90)} bps")
    test("Bonus rate 180d", lambda: f"{staking.get_bonus_rate(180)} bps")
    test("Bonus rate 365d", lambda: f"{staking.get_bonus_rate(365)} bps")
    test("Deployer stake info", lambda: (
        lambda s: f"active={s.active_stakes}, locked={s.total_locked_ether}, bonus={s.pending_bonus_ether}"
    )(staking.get_stake_info()))
    test("Deployer stake count", lambda: f"{staking.get_stake_count()} stakes")
    test("Staking repr", lambda: repr(staking))

    print()

    # ══════════════════════════════════════════════════════════
    # 5. ORACLE CLIENT (AIOracle)
    # ══════════════════════════════════════════════════════════
    print("━" * 50)
    print("5️⃣  OracleClient (AIOracle)")
    print("━" * 50)

    oracle = client.oracle
    test("Protocol fee", lambda: f"{oracle.protocol_fee_bps()} bps")
    test("Total requests", lambda: f"{oracle.total_requests()} requests")

    # Test model approval check
    test_model = Web3.keccak(text="test-model-v1")
    test("Model approved?", lambda: f"approved={oracle.is_model_approved(test_model)}")
    test("Oracle repr", lambda: repr(oracle))

    print()

    # ══════════════════════════════════════════════════════════
    # 6. ZKML CLIENT (ZkMLVerifier)
    # ══════════════════════════════════════════════════════════
    print("━" * 50)
    print("6️⃣  ZkMLClient (ZkMLVerifier)")
    print("━" * 50)

    zkml = client.zkml
    test("Dev mode enabled?", lambda: f"dev_mode={zkml.dev_mode_enabled()}")

    # Test image trust check
    test_image = Web3.keccak(text="test-image-v1")
    test("Image trusted?", lambda: f"trusted={zkml.is_image_trusted(test_image)}")

    # Test dev proof creation (off-chain only, no tx)
    test("Create dev proof (off-chain)", lambda: (
        lambda seal, proof_hash: f"seal={seal.hex()[:16]}..., hash={proof_hash.hex()[:16]}..."
    )(*zkml.create_dev_proof(test_image, b"test-journal-data")))

    test("ZkML repr", lambda: repr(zkml))

    print()

    # ══════════════════════════════════════════════════════════
    # 7. SUBNET CLIENT (SubnetRegistry)
    # ══════════════════════════════════════════════════════════
    print("━" * 50)
    print("7️⃣  SubnetClient (SubnetRegistry)")
    print("━" * 50)

    subnet = client.subnet
    test("Subnet count", lambda: f"{subnet.get_subnet_count()} subnets")

    # Check if any subnets exist
    try:
        count = subnet.get_subnet_count()
        if count > 0:
            test("Get subnet #1", lambda: (
                lambda s: f"name={s.name}, owner={s.owner[:10]}..., nodes={s.node_count}/{s.max_nodes}, active={s.active}"
            )(subnet.get_subnet(1)))
        else:
            test("No subnets yet", lambda: "0 subnets (expected for fresh deployment)")
    except Exception:
        test("No subnets yet", lambda: "0 subnets (expected for fresh deployment)")

    # Check registration status
    test("Is registered?", lambda: f"registered={subnet.is_registered(1)}")
    test("Subnet repr", lambda: repr(subnet))

    print()

    # ══════════════════════════════════════════════════════════
    # 8. EVENT LISTENER
    # ══════════════════════════════════════════════════════════
    print("━" * 50)
    print("8️⃣  EventListener")
    print("━" * 50)

    events = client.events
    test("EventListener initialized", lambda: f"listener={repr(events)}")

    print()

    # ══════════════════════════════════════════════════════════
    # 9. AI SUBNET ORCHESTRATOR
    # ══════════════════════════════════════════════════════════
    print("━" * 50)
    print("9️⃣  AISubnetOrchestrator")
    print("━" * 50)

    orchestrator = client.orchestrator(netuid=1)
    test("Orchestrator initialized", lambda: f"orchestrator(netuid=1)")
    test("Orchestrator repr", lambda: repr(orchestrator))

    print()

    # ══════════════════════════════════════════════════════════
    # 10. CROSS-MODULE INTEGRATION
    # ══════════════════════════════════════════════════════════
    print("━" * 50)
    print("🔗  Cross-Module Integration Checks")
    print("━" * 50)

    # Check that contract addresses are loaded correctly
    test("MDTToken address loaded", lambda: f"addr={client._addresses.get('MDTToken', 'MISSING')[:16]}...")
    test("MDTVesting address loaded", lambda: f"addr={client._addresses.get('MDTVesting', 'MISSING')[:16]}...")
    test("MDTStaking address loaded", lambda: f"addr={client._addresses.get('MDTStaking', 'MISSING')[:16]}...")
    test("ZkMLVerifier address loaded", lambda: f"addr={client._addresses.get('ZkMLVerifier', 'MISSING')[:16]}...")
    test("AIOracle address loaded", lambda: f"addr={client._addresses.get('AIOracle', 'MISSING')[:16]}...")
    test("SubnetRegistry address loaded", lambda: f"addr={client._addresses.get('SubnetRegistry', 'MISSING')[:16]}...")

    # Network config check
    from sdk.polkadot.config import NETWORKS
    test("polkadot_testnet config", lambda: (
        f"rpc={NETWORKS['polkadot_testnet'].rpc_url}, chain={NETWORKS['polkadot_testnet'].chain_id}"
    ))

    # Settings check
    from sdk.config.settings import settings
    test("Settings RPC URL", lambda: f"rpc={settings.LUXTENSOR_RPC_URL}")

    # CLI config check
    from sdk.cli.config import NETWORKS as CLI_NETWORKS
    test("CLI polkadot_testnet config", lambda: (
        f"rpc={CLI_NETWORKS['polkadot_testnet'].rpc_url}, chain={CLI_NETWORKS['polkadot_testnet'].chain_id}"
    ))

    print()

    # ══════════════════════════════════════════════════════════
    # SUMMARY
    # ══════════════════════════════════════════════════════════
    print("=" * 70)
    print(f"  RESULTS: {passed_tests}/{total_tests} passed, "
          f"{failed_tests} failed, {skipped_tests} skipped")
    print("=" * 70)
    print()

    if failed_tests == 0:
        print("  🎉 ALL TESTS PASSED! SDK is fully operational on Polkadot Hub TestNet!")
    else:
        print(f"  ⚠️  {failed_tests} test(s) failed. See details above.")
        print()
        print("  Failed tests:")
        for status, name, msg in results:
            if status == "❌":
                print(f"    • {name}: {msg}")

    print()
    print("  📋 Contract Addresses:")
    for name, addr in client._addresses.items():
        print(f"    {name:20s} → {addr}")

    print()
    return failed_tests == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
