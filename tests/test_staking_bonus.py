"""
Staking Bonus Pool + Lock Verification Test

Tests:
1. Bonus pool balance check (safety)
2. Lock operation with bonus rate preview
3. Stake info verification
4. Emission config query

Run:  python tests/test_staking_bonus.py
"""

import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web3 import Web3

# ──────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────

PRIVATE_KEY = "0x3230cd6d7ea8c1666bcec73a86a1a8d86ad23198bf29554bf11f61bed41452fb"
DEPLOYMENT_PATH = "luxtensor/contracts/deployments-polkadot.json"
NETWORK = "polkadot_testnet"

passed = 0
failed = 0
results = []


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

    print("=" * 60)
    print("  Staking Bonus Pool + Emission Config Test")
    print("  Network: Polkadot Hub TestNet")
    print("=" * 60)
    print()

    from sdk.polkadot.client import PolkadotClient

    client = PolkadotClient(
        network=NETWORK,
        private_key=PRIVATE_KEY,
        deployment_path=DEPLOYMENT_PATH,
    )

    print(f"  Deployer: {client.address}")
    print()

    # ═══════════════════════════════════════════════════════
    # TEST 1: Staking Read Operations
    # ═══════════════════════════════════════════════════════
    print("━" * 50)
    print("TEST 1: Staking Read Operations")
    print("━" * 50)

    staking = client.staking

    step("Total staked", lambda: f"{Web3.from_wei(staking.total_staked(), 'ether')} MDT")
    step("Total bonus paid", lambda: f"{Web3.from_wei(staking.total_bonus_paid(), 'ether')} MDT")

    # NEW: Bonus pool balance check
    step("Bonus pool balance",
         lambda: f"{staking.bonus_pool_balance_ether():.4f} MDT")

    step("Stake count for deployer", lambda: f"{staking.get_stake_count()} stakes")

    # Bonus rate preview
    step("Bonus rate for 30d", lambda: f"{staking.get_bonus_rate(30)} bps (10%)")
    step("Bonus rate for 90d", lambda: f"{staking.get_bonus_rate(90)} bps (25%)")
    step("Bonus rate for 180d", lambda: f"{staking.get_bonus_rate(180)} bps (50%)")
    step("Bonus rate for 365d", lambda: f"{staking.get_bonus_rate(365)} bps (100%)")
    step("Bonus rate for 15d", lambda: f"{staking.get_bonus_rate(15)} bps (0%)")
    print()

    # ═══════════════════════════════════════════════════════
    # TEST 2: Stake Info
    # ═══════════════════════════════════════════════════════
    print("━" * 50)
    print("TEST 2: Deployer Stake Info")
    print("━" * 50)

    step("Stake info",
         lambda: (
             lambda s: f"active={s.active_stakes}, locked={s.total_locked_ether} MDT, bonus={s.pending_bonus_ether} MDT"
         )(staking.get_stake_info()))

    # Show all stakes
    stake_count = staking.get_stake_count()
    if stake_count > 0:
        for i in range(min(stake_count, 5)):
            step(f"Stake lock #{i}",
                 lambda idx=i: (
                     lambda s: f"amount={s.amount_ether} MDT, bonus={s.bonus_percent}%, withdrawn={s.withdrawn}, can_unlock={s.can_unlock}"
                 )(staking.get_stake_lock(idx)))
    print()

    # ═══════════════════════════════════════════════════════
    # TEST 3: Emission Config (SubnetRegistry)
    # ═══════════════════════════════════════════════════════
    print("━" * 50)
    print("TEST 3: Emission & Security Config")
    print("━" * 50)

    subnet = client.subnet

    step("Emission config",
         lambda: (
             lambda c: (
                 f"emission/block={c['emission_per_block']}, "
                 f"shares={c['total_emission_shares']}, "
                 f"slash={c['slash_percentage']}bps, "
                 f"reveal_window={c['commit_reveal_window']}blk, "
                 f"reg_cost={c['subnet_registration_cost']}"
             )
         )(subnet.get_emission_config()))

    print()

    # ═══════════════════════════════════════════════════════
    # TEST 4: Bonus Pool Safety Check
    # ═══════════════════════════════════════════════════════
    print("━" * 50)
    print("TEST 4: Bonus Pool Safety Check")
    print("━" * 50)

    bonus_pool = staking.bonus_pool_balance()
    pending_bonus = staking.get_stake_info().pending_bonus

    if pending_bonus > 0:
        coverage = (bonus_pool / pending_bonus * 100) if pending_bonus > 0 else 0
        if bonus_pool >= pending_bonus:
            passed += 1
            results.append(("✅", "Bonus pool coverage", f"{coverage:.0f}% — sufficient"))
            print(f"  ✅ Bonus pool coverage: {coverage:.0f}% — sufficient")
        else:
            deficit = Web3.from_wei(pending_bonus - bonus_pool, "ether")
            failed += 1
            results.append(("⚠️", "Bonus pool coverage", f"{coverage:.0f}% — DEFICIT {deficit} MDT"))
            print(f"  ⚠️  Bonus pool coverage: {coverage:.0f}% — DEFICIT {deficit} MDT")
            print(f"     → Owner should call: staking.fund_bonus_pool({deficit})")
    else:
        passed += 1
        results.append(("✅", "Bonus pool check", "No pending bonuses"))
        print(f"  ✅ No pending bonuses — pool not needed yet")
    print()

    # ═══════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════
    print("=" * 60)
    print(f"  RESULTS: {passed}/{passed+failed} passed, {failed} failed")
    print("=" * 60)

    if failed == 0:
        print("  🎉 ALL STAKING TESTS PASSED!")
    else:
        print(f"  ⚠️  {failed} issue(s):")
        for status, name, msg in results:
            if status == "❌" or status == "⚠️":
                print(f"    • {name}: {msg}")

    print()
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
