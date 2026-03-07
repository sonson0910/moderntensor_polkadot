#!/usr/bin/env python3
"""
Polkadot Hub Testnet — On-Chain Verification.

Tests deployed contracts on the REAL Polkadot Hub Testnet (chainId 420420417).
This proves the code runs on a real blockchain, not just local Hardhat.
"""

import json
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web3 import Web3

# ── Config ──────────────────────────────────────────────────
RPC_URL = "https://services.polkadothub-rpc.com/testnet"
EXPECTED_CHAIN_ID = 420420417
PRIVATE_KEY = os.environ.get("TESTNET_PRIVATE_KEY", "0x3230cd6d7ea8c1666bcec73a86a1a8d86ad23198bf29554bf11f61bed41452fb")

DEPLOY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "luxtensor", "contracts", "deployments-polkadot.json",
)

# Test tracking
results = []
passed = 0
failed = 0


def test(name, func):
    """Run a test and track result."""
    global passed, failed
    try:
        t0 = time.time()
        result = func()
        dt = time.time() - t0
        passed += 1
        results.append(("✅", name, str(result)))
        print(f"  ✅ {name}: {result}  ({dt:.1f}s)")
    except Exception as e:
        failed += 1
        results.append(("❌", name, str(e)))
        print(f"  ❌ {name}: {e}")
        traceback.print_exc()


def _send_tx(w3, contract_fn, sender, value=0, gas=500000):
    """Build, sign, and send a transaction on Polkadot Hub Testnet."""
    tx = contract_fn.build_transaction({
        "from": sender.address,
        "nonce": w3.eth.get_transaction_count(sender.address),
        "gas": gas,
        "gasPrice": w3.eth.gas_price,
        "chainId": EXPECTED_CHAIN_ID,
        "value": value,
    })
    signed = sender.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"    → TX sent: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    if receipt["status"] != 1:
        raise Exception(f"TX REVERTED: {tx_hash.hex()}")
    print(f"    → Block: {receipt['blockNumber']}, Gas: {receipt['gasUsed']}")
    return receipt


def main():
    global passed, failed

    print("=" * 70)
    print("  ModernTensor — POLKADOT HUB TESTNET Verification")
    print(f"  RPC: {RPC_URL}")
    print(f"  Chain ID: {EXPECTED_CHAIN_ID}")
    print("=" * 70)
    print()

    # ── Connect to Polkadot Hub Testnet ──
    w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 30}))
    if not w3.is_connected():
        print("❌ Cannot connect to Polkadot Hub Testnet!")
        return False

    chain_id = w3.eth.chain_id
    block = w3.eth.block_number
    print(f"  🔗 Connected! Chain ID: {chain_id}, Block: {block}")

    if chain_id != EXPECTED_CHAIN_ID:
        print(f"  ⚠️  Unexpected chain ID: {chain_id} (expected {EXPECTED_CHAIN_ID})")

    deployer = w3.eth.account.from_key(PRIVATE_KEY)
    balance = w3.eth.get_balance(deployer.address)
    print(f"  👤 Deployer: {deployer.address}")
    print(f"  💰 Balance: {Web3.from_wei(balance, 'ether')} WND")
    print()

    if balance == 0:
        print("  ⚠️  No balance — some TX tests will fail")
        print()

    # ── Load deployment ──
    with open(DEPLOY_PATH) as f:
        deploy = json.load(f)
    contracts = deploy["contracts"]

    # ── Load ABIs ──
    def load_abi(name):
        base = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "luxtensor", "contracts", "artifacts", "src",
        )
        for sub in ["", "templates/", "examples/"]:
            p = os.path.join(base, sub, f"{name}.sol", f"{name}.json")
            if os.path.exists(p):
                with open(p) as f:
                    return json.load(f)["abi"]
        raise FileNotFoundError(f"ABI not found: {name}")

    # ═══════════════════════════════════════════════
    # TEST 1: Contract Existence & Read Calls
    # ═══════════════════════════════════════════════
    print("━" * 50)
    print("1️⃣  Contract Read Calls (on-chain!)")
    print("━" * 50)

    token = w3.eth.contract(address=contracts["MDTToken"], abi=load_abi("MDTToken"))
    zkml = w3.eth.contract(address=contracts["ZkMLVerifier"], abi=load_abi("ZkMLVerifier"))
    oracle = w3.eth.contract(address=contracts["AIOracle"], abi=load_abi("AIOracle"))
    subnet = w3.eth.contract(address=contracts["SubnetRegistry"], abi=load_abi("SubnetRegistry"))

    test("MDTToken.name()", lambda: token.functions.name().call())
    test("MDTToken.symbol()", lambda: token.functions.symbol().call())
    test("MDTToken.totalSupply()", lambda: f"{Web3.from_wei(token.functions.totalSupply().call(), 'ether')} MDT")
    test("Deployer MDT balance", lambda: f"{Web3.from_wei(token.functions.balanceOf(deployer.address).call(), 'ether')} MDT")
    print()

    # ═══════════════════════════════════════════════
    # TEST 2: ZkMLVerifier State
    # ═══════════════════════════════════════════════
    print("━" * 50)
    print("2️⃣  ZkMLVerifier On-Chain State")
    print("━" * 50)

    test("devModeEnabled", lambda: f"{zkml.functions.devModeEnabled().call()}")
    test("maxProofAge", lambda: f"{zkml.functions.maxProofAge().call()} blocks")
    test("Contract address exists", lambda: (
        f"code_size={len(w3.eth.get_code(contracts['ZkMLVerifier']))} bytes"
    ))
    print()

    # ═══════════════════════════════════════════════
    # TEST 3: SubnetRegistry State
    # ═══════════════════════════════════════════════
    print("━" * 50)
    print("3️⃣  SubnetRegistry On-Chain State")
    print("━" * 50)

    test("getSubnetCount()", lambda: f"{subnet.functions.getSubnetCount().call()} subnets")
    test("Contract code", lambda: (
        f"code_size={len(w3.eth.get_code(contracts['SubnetRegistry']))} bytes"
    ))
    print()

    # ═══════════════════════════════════════════════
    # TEST 4: AIOracle State
    # ═══════════════════════════════════════════════
    print("━" * 50)
    print("4️⃣  AIOracle On-Chain State")
    print("━" * 50)

    test("requestCount()", lambda: f"{oracle.functions.requestCount().call()} requests")
    test("Contract code", lambda: (
        f"code_size={len(w3.eth.get_code(contracts['AIOracle']))} bytes"
    ))
    print()

    # ═══════════════════════════════════════════════
    # TEST 5: Write TX — Trust Image + Verify Dev Proof
    # ═══════════════════════════════════════════════
    if balance > 0:
        print("━" * 50)
        print("5️⃣  Write TX — zkML Dev Proof on Polkadot Hub Testnet")
        print("━" * 50)

        def _test_zkml_write():
            test_model = f"testnet-model-{int(time.time())}"
            image_id = Web3.keccak(text=test_model)

            # Trust image
            print(f"    Trusting image: {image_id.hex()[:16]}...")
            _send_tx(w3, zkml.functions.trustImage(image_id), deployer)

            # Verify trusted
            is_trusted = zkml.functions.trustedImages(image_id).call()
            if not is_trusted:
                raise Exception("Image not trusted after TX!")

            # Create and verify dev proof
            journal = f"Testnet verification at {time.strftime('%H:%M:%S')}".encode()
            seal = Web3.keccak(Web3.keccak(image_id) + Web3.keccak(journal))

            print(f"    Verifying dev proof...")
            receipt = _send_tx(w3, zkml.functions.verifyProof(image_id, journal, seal, 2), deployer)

            return f"✅ Dev proof verified! Block={receipt['blockNumber']}, Gas={receipt['gasUsed']}"

        test("zkML trust + verify (REAL TX)", _test_zkml_write)
        print()

    else:
        print("━" * 50)
        print("5️⃣  ⏭️  Skipping write TX (no balance)")
        print("━" * 50)
        print()

    # ═══════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════
    total = passed + failed
    print("=" * 70)
    print(f"  RESULTS: {passed}/{total} passed, {failed} failed")
    print(f"  Network: Polkadot Hub Testnet (chainId {chain_id})")
    print(f"  Block: {w3.eth.block_number}")
    print("=" * 70)

    if failed == 0:
        print("  🎉 ALL ON-CHAIN TESTS PASSED!")
    else:
        print(f"  ⚠️  {failed} test(s) failed")

    print()
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
