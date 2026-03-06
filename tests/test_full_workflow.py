"""
Full Workflow Integration Test — Write Transactions on Polkadot Hub TestNet

Tests the entire lifecycle with SubnetRegistry v2 support:
  STEP 1: TGE — Mint MDT tokens (EmissionRewards category)
  STEP 2: Token Transfer — Transfer MDT between accounts
  STEP 3: ZkML — Trust image → Create dev proof → Verify on-chain
  STEP 4: Oracle — Approve model → Submit AI request → Fulfill
  STEP 5: Subnet v2 — Create subnet → Register node (self-vote protection)
  STEP 6: Staking — Approve MDT → Lock stake
  STEP 7: Commit-Reveal Weights — Test commit + reveal flow

Run:  python tests/test_full_workflow.py
"""

import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web3 import Web3

# ──────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────

PRIVATE_KEY = os.environ.get(
    "TESTNET_PRIVATE_KEY", "0x3230cd6d7ea8c1666bcec73a86a1a8d86ad23198bf29554bf11f61bed41452fb"
)
DEPLOYMENT_PATH = "luxtensor/contracts/deployments-polkadot.json"
NETWORK = "polkadot_testnet"

results = []
passed = 0
failed = 0


def step(name, func):
    global passed, failed
    try:
        result = func()
        passed += 1
        results.append(("✅", name, str(result)))
        print(f"  ✅ {name}: {result}")
        return result
    except Exception as e:
        failed += 1
        msg = str(e)[:200]
        results.append(("❌", name, msg))
        print(f"  ❌ {name}: {msg}")
        traceback.print_exc()
        return None


def main():
    global passed, failed

    print("=" * 70)
    print("  ModernTensor — Full Workflow Test (SubnetRegistry v2)")
    print("  Network: Polkadot Hub TestNet (420420417)")
    print("=" * 70)
    print()

    # ── Init Client ──────────────────────────────────────────
    from sdk.polkadot.client import PolkadotClient

    client = PolkadotClient(
        network=NETWORK,
        private_key=PRIVATE_KEY,
        deployment_path=DEPLOYMENT_PATH,
    )

    deployer = client.address
    print(f"  Deployer: {deployer}")
    bal = Web3.from_wei(client.get_eth_balance(), "ether")
    print(f"  Balance:  {bal} PAS")
    print()

    # ═══════════════════════════════════════════════════════
    # STEP 1: TGE — Mint MDT Tokens
    # ═══════════════════════════════════════════════════════
    print("━" * 50)
    print("STEP 1: TGE — Mint MDT Tokens")
    print("━" * 50)

    token = client.token

    # Check current state
    supply_before = token.total_supply()
    tge_done = token.tge_executed()
    print(f"  Current supply: {Web3.from_wei(supply_before, 'ether')} MDT")
    print(f"  TGE executed:   {tge_done}")

    if not tge_done:
        # Mint EmissionRewards category (category 0) to deployer
        tx = step(
            "TGE: Mint EmissionRewards (cat=0)",
            lambda: token.execute_tge(category=token.CAT_EMISSION_REWARDS, to=deployer),
        )

        if tx:
            supply_after = token.total_supply()
            balance_after = token.balance_of_ether()
            print(f"  → Supply after TGE:  {Web3.from_wei(supply_after, 'ether')} MDT")
            print(f"  → Deployer balance:  {balance_after} MDT")
    else:
        print("  ⏭️  TGE already executed, skipping")

    # Check balance
    step("Deployer MDT balance", lambda: f"{token.balance_of_ether()} MDT")
    print()

    # ═══════════════════════════════════════════════════════
    # STEP 2: Token Transfer
    # ═══════════════════════════════════════════════════════
    print("━" * 50)
    print("STEP 2: Token Transfer")
    print("━" * 50)

    current_balance = token.balance_of()
    if current_balance > 0:
        # Transfer 1 MDT to a burn address (just to test)
        burn_addr = "0x000000000000000000000000000000000000dEaD"
        transfer_amount = Web3.to_wei(1, "ether")  # 1 MDT
        step("Transfer 1 MDT to burn address", lambda: token.transfer(burn_addr, transfer_amount))

        step("Balance after transfer", lambda: f"{token.balance_of_ether()} MDT")
    else:
        print("  ⏭️  No MDT balance, skipping transfer")
    print()

    # ═══════════════════════════════════════════════════════
    # STEP 3: ZkML — Trust Image + Verify Proof On-Chain
    # ═══════════════════════════════════════════════════════
    print("━" * 50)
    print("STEP 3: ZkML — On-Chain Proof Verification")
    print("━" * 50)

    zkml = client.zkml

    # 3a. Enable dev mode (required for dev proof verification)
    step("Enable ZkML dev mode", lambda: zkml.set_dev_mode(True))
    step("Dev mode enabled?", lambda: f"devMode={zkml.dev_mode_enabled()}")

    # 3b. Trust a test image ID
    test_image_id = Web3.keccak(text="moderntensor-code-review-v1")
    step("Trust image ID", lambda: zkml.trust_image(test_image_id))

    # 3c. Verify image is trusted
    step("Image trusted?", lambda: f"trusted={zkml.is_image_trusted(test_image_id)}")

    # 3d. Create dev proof (off-chain)
    journal = b"code_review_score:95,model:gpt4,subnet:1"
    seal, proof_hash = zkml.create_dev_proof(test_image_id, journal)
    print(f"  Dev proof created: seal={seal.hex()[:16]}...")

    # 3e. Verify proof on-chain (write tx!)
    step(
        "Verify dev proof on-chain",
        lambda: zkml.verify_proof(
            image_id=test_image_id, journal=journal, seal=seal, proof_type=2  # PROOF_TYPE_DEV
        ),
    )

    # 3f. Check verification result
    step(
        "Get verification result",
        lambda: (
            lambda v: f"valid={v.is_valid}, verifier={v.verifier[:10]}..., at={v.verified_at}"
        )(zkml.get_verification(proof_hash)),
    )

    print()

    # ═══════════════════════════════════════════════════════
    # STEP 4: Oracle — Full AI Request Lifecycle
    # ═══════════════════════════════════════════════════════
    print("━" * 50)
    print("STEP 4: Oracle — AI Request Lifecycle")
    print("━" * 50)

    oracle = client.oracle

    # 4a. Approve model
    model_hash = Web3.keccak(text="moderntensor-code-review-v1")
    step("Approve AI model", lambda: oracle.approve_model(model_hash))
    step("Model approved?", lambda: f"approved={oracle.is_model_approved(model_hash)}")

    # 4b. Link ZkML verifier to Oracle
    zkml_addr = client._addresses.get("ZkMLVerifier")
    step("Set ZkMLVerifier on Oracle", lambda: oracle.set_zkml_verifier(zkml_addr))

    # 4c. Submit AI request (with 0.01 PAS payment)
    input_data = b'{"code":"def hello(): return 42","lang":"python"}'
    req_count_before = oracle.total_requests()
    step(
        "Submit AI request (0.01 PAS)",
        lambda: oracle.request_ai(
            model_hash=model_hash,
            input_data=input_data,
            timeout=0,
            payment_ether=0.01,
        ),
    )

    req_count_after = oracle.total_requests()
    print(f"  → Requests: {req_count_before} → {req_count_after}")

    # 4d. Get request details
    if req_count_after > req_count_before:
        step("Total requests after", lambda: f"{oracle.total_requests()} requests")

    # 4e. Verify the request was created
    step("Oracle total requests", lambda: f"{oracle.total_requests()}")

    print()

    # ═══════════════════════════════════════════════════════
    # STEP 5: Subnet v2 — Create + Register Node
    # ═══════════════════════════════════════════════════════
    print("━" * 50)
    print("STEP 5: Subnet v2 — Create + Register (Self-Vote Protection)")
    print("━" * 50)

    subnet = client.subnet

    subnet_count_before = subnet.get_subnet_count()
    print(f"  Subnets before: {subnet_count_before}")

    # 5a. Approve MDT for SubnetRegistry (registration cost burns MDT)
    subnet_addr = client._addresses.get("SubnetRegistry")
    approve_for_subnet = Web3.to_wei(100, "ether")  # 100 MDT should cover registration
    step(
        "Approve 100 MDT for SubnetRegistry", lambda: token.approve(subnet_addr, approve_for_subnet)
    )

    # 5b. Create subnet — returns (tx_hash, netuid)
    create_result = [None]

    def do_create_subnet():
        tx_hash, netuid = subnet.create_subnet(
            name="AI-CodeReview",
            max_nodes=256,
            min_stake_ether=0,
            tempo=360,
        )
        create_result[0] = netuid
        return f"tx={tx_hash[:16]}..., netuid={netuid}"

    step("Create subnet 'AI-CodeReview'", do_create_subnet)

    netuid = create_result[0]
    if netuid is not None:
        subnet_count_after = subnet.get_subnet_count()
        print(f"  Subnets after: {subnet_count_after}")
        print(f"  Assigned netuid: {netuid}")

        # 5c. Get subnet info (v2 fields)
        step(
            f"Get subnet #{netuid}",
            lambda: (
                lambda s: f"name={s.name}, owner={s.owner[:10]}..., max={s.max_nodes}, active={s.active}"
            )(subnet.get_subnet(netuid)),
        )

        # 5d. Register as MINER
        step(
            f"Register MINER in subnet #{netuid}",
            lambda: subnet.register_miner(
                netuid=netuid,
                stake_ether=0,
            ),
        )

        # 5e. Check registration
        step("Is registered?", lambda: f"registered={subnet.is_registered(netuid)}")

        # 5f. Verify self-vote protection (v2) — same coldkey can't be both miner+validator
        print("  🔒 Self-Vote Protection Test:")
        try:
            subnet.register_validator(netuid=netuid, stake_ether=0)
            # If we get here, it means self-vote protection didn't work
            failed += 1
            results.append(("❌", "Self-vote protection", "Should have rejected dual registration"))
            print("  ❌ Self-vote protection: Should have rejected dual registration")
        except Exception as e:
            if (
                "Already registered" in str(e)
                or "same subnet" in str(e)
                or "revert" in str(e).lower()
            ):
                passed += 1
                results.append(
                    ("✅", "Self-vote protection", "Correctly rejected dual registration")
                )
                print(f"  ✅ Self-vote protection: Correctly rejected dual registration")
            else:
                failed += 1
                results.append(("❌", "Self-vote protection", str(e)[:100]))
                print(f"  ❌ Self-vote protection: {str(e)[:100]}")

        # 5g. Get node info with v2 fields (including trust)
        step(
            f"Get node info (v2: includes trust)",
            lambda: (
                lambda n: f"uid={n.uid}, type={n.node_type}, active={n.active}, trust={n.trust}"
            )(subnet.get_node(netuid, 0)),
        )

    print()

    # ═══════════════════════════════════════════════════════
    # STEP 6: Staking — Approve MDT + Lock
    # ═══════════════════════════════════════════════════════
    print("━" * 50)
    print("STEP 6: Staking — Lock MDT Tokens")
    print("━" * 50)

    staking = client.staking
    current_mdt = token.balance_of()

    if current_mdt >= Web3.to_wei(10, "ether"):
        staking_addr = client._addresses.get("MDTStaking")

        # 6a. Approve MDT for staking contract
        approve_amount = Web3.to_wei(10, "ether")
        step("Approve 10 MDT for staking", lambda: token.approve(staking_addr, approve_amount))

        # 6b. Lock tokens for 30 days (10% bonus)
        step("Lock 10 MDT for 30 days", lambda: staking.lock(amount_ether=10, lock_days=30))

        # 6c. Check stake info
        step(
            "Stake info after lock",
            lambda: (
                lambda s: f"active={s.active_stakes}, locked={s.total_locked_ether} MDT, bonus={s.pending_bonus_ether} MDT"
            )(staking.get_stake_info()),
        )

        step(
            "Total staked (global)", lambda: f"{Web3.from_wei(staking.total_staked(), 'ether')} MDT"
        )
    else:
        balance_mdt = Web3.from_wei(current_mdt, "ether")
        print(f"  ⏭️  Insufficient MDT balance ({balance_mdt} MDT), need >= 10 MDT for staking test")
    print()

    # ═══════════════════════════════════════════════════════
    # STEP 7: Commit-Reveal Weights (v2 Security Feature)
    # ═══════════════════════════════════════════════════════
    print("━" * 50)
    print("STEP 7: Commit-Reveal Weights (Anti Front-Running)")
    print("━" * 50)

    if netuid is not None:
        print("  Testing commit-reveal weight flow...")

        # 7a. Commit weights
        commit_result = [None]

        def do_commit():
            tx_hash, salt = subnet.commit_weights(
                netuid=netuid,
                uids=[0],  # miner UID 0
                weights=[5000],  # weight 0.5
            )
            commit_result[0] = salt
            return f"tx={tx_hash[:16]}..., salt={salt.hex()[:16]}..."

        step("Commit weights (commit phase)", do_commit)

        # 7b. Attempt reveal (may fail if window hasn't opened yet)
        if commit_result[0] is not None:
            salt = commit_result[0]
            step(
                "Reveal weights (reveal phase)",
                lambda: subnet.reveal_weights(
                    netuid=netuid,
                    uids=[0],
                    weights=[5000],
                    salt=salt,
                ),
            )
    else:
        print("  ⏭️  No subnet created, skipping commit-reveal test")
    print()

    # ═══════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════
    print("=" * 70)
    print(f"  RESULTS: {passed}/{passed+failed} passed, {failed} failed")
    print("=" * 70)
    print()

    # Final balances
    final_pas = Web3.from_wei(client.get_eth_balance(), "ether")
    final_mdt = token.balance_of_ether()
    print(f"  💰 Final PAS: {final_pas}")
    print(f"  🪙 Final MDT: {final_mdt}")
    print(f"  📊 Gas used:  {float(bal) - float(final_pas):.6f} PAS")
    print()

    if failed == 0:
        print("  🎉 ALL WORKFLOW STEPS PASSED!")
    else:
        print(f"  ⚠️  {failed} step(s) failed:")
        for status, name, msg in results:
            if status == "❌":
                print(f"    • {name}: {msg}")

    print()
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
