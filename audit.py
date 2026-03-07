#!/usr/bin/env python3
"""Deep Feature Completeness Audit — checks LOGIC not just files."""
import json, os, ast, re

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

PASS = "[OK     ]"
FAIL = "[MISSING]"
WARN = "[WARN   ]"

gaps = []  # Collect all gaps


def check(condition, label, detail=""):
    if condition:
        print(f"  {PASS} {label}")
    else:
        gaps.append((label, detail))
        print(f"  {FAIL} {label} — {detail}")


def warn(label, detail=""):
    gaps.append((label, detail))
    print(f"  {WARN} {label} — {detail}")


# ══════════════════════════════════════════════════════════
print("=" * 70)
print("DEEP FEATURE COMPLETENESS AUDIT")
print("=" * 70)

# ══════════════════════════════════════════════════════════
# 1. SMART CONTRACTS — check each has expected functions
# ══════════════════════════════════════════════════════════
print("\n## 1. SMART CONTRACTS — Function Coverage")

contracts_check = {
    "SubnetRegistry": [
        "createSubnet",
        "registerNode",
        "deregisterNode",
        "setWeights",
        "runEpoch",
        "claimEmission",
        "delegate",
        "undelegate",
        "getMetagraph",
        "getNode",
        "getSubnet",
        "fundEmissionPool",
        "isRegistered",
    ],
    "MDTToken": ["executeTGE", "transfer", "approve", "totalSupply", "balanceOf"],
    "MDTVesting": ["createIDOVesting", "claim", "getVestingInfo", "vestedAmount", "claimable"],
    "MDTStaking": ["lock", "unlock", "getStakeInfo", "getStakeLock"],
    "AIOracle": ["requestAI", "fulfillRequest", "approveModel"],
    "GradientAggregator": ["createJob", "submitGradient", "registerAsTrainer"],
    "TrainingEscrow": ["stake", "fundJob"],
    "PaymentEscrow": ["deposit", "refund"],
    "ZkMLVerifier": ["verifyProof", "setDevMode"],
}

for contract, expected_fns in contracts_check.items():
    abi_path = f"sdk/contracts/abis/{contract}.json"
    if not os.path.exists(abi_path):
        check(False, f"{contract} ABI", "ABI file missing")
        continue
    with open(abi_path) as f:
        abi = json.load(f)
    fn_names = [item["name"] for item in abi if item.get("type") == "function"]
    for fn in expected_fns:
        check(fn in fn_names, f"{contract}.{fn}()", f"not in ABI ({len(fn_names)} fns)")

# ══════════════════════════════════════════════════════════
# 2. SDK WRAPPERS — check each method exists in Python
# ══════════════════════════════════════════════════════════
print("\n## 2. SDK WRAPPERS — Method Coverage")

sdk_checks = {
    "sdk/polkadot/token.py": [
        "balance_of",
        "transfer",
        "approve",
        "total_supply",
    ],
    "sdk/polkadot/staking.py": [
        "lock",
        "unlock",
        "get_stake",
    ],
    "sdk/polkadot/oracle.py": [
        "request_ai",
        "fulfill_request",
        "approve_model",
    ],
    "sdk/polkadot/training.py": [
        "create_job",
        "submit_gradient",
        "register_as_trainer",
    ],
    "sdk/polkadot/escrow.py": [
        "stake",
        "fund_job",
        "deposit",
        "refund",
    ],
    "sdk/polkadot/zkml.py": [
        "verify",
        "set_dev_mode",
    ],
    "sdk/polkadot/subnet.py": [
        "create_subnet",
        "register_miner",
        "register_validator",
        "deregister",
        "set_weights",
        "get_weights",
        "run_epoch",
        "claim_emission",
        "delegate",
        "undelegate",
        "get_metagraph",
        "get_node",
        "get_subnet",
        "is_registered",
        "get_uid",
        "approve_and_register_miner",
        "approve_and_register_validator",
        "approve_and_delegate",
    ],
    "sdk/polkadot/events.py": [
        "listen",
        "get_events",
    ],
    "sdk/polkadot/client.py": [
        "send_tx",
        "get_eth_balance",
    ],
}

for filepath, expected_methods in sdk_checks.items():
    if not os.path.exists(filepath):
        check(False, f"{filepath}", "file missing")
        continue
    with open(filepath) as f:
        content = f.read()
    for method in expected_methods:
        found = f"def {method}" in content
        check(found, f"{os.path.basename(filepath)}::{method}()")

# ══════════════════════════════════════════════════════════
# 3. CLIENT INTEGRATION — check client.py has all sub-clients
# ══════════════════════════════════════════════════════════
print("\n## 3. POLKADOT CLIENT — Sub-Client Properties")

with open("sdk/polkadot/client.py") as f:
    client_src = f.read()

sub_clients = ["token", "staking", "oracle", "training", "escrow", "zkml", "events", "subnet"]
for sc in sub_clients:
    check(f"def {sc}(self)" in client_src, f"client.{sc}", "property missing")

# ══════════════════════════════════════════════════════════
# 4. CLI COMMANDS — wallet operations
# ══════════════════════════════════════════════════════════
print("\n## 4. CLI COMMANDS — Wallet")

with open("sdk/cli/commands/wallet.py") as f:
    wallet_src = f.read()

cli_cmds = [
    ("wallet create-coldkey", "'create-coldkey'"),
    ("wallet restore-coldkey", "'restore-coldkey'"),
    ("wallet list", "'list'"),
    ("wallet generate-hotkey", "'generate-hotkey'"),
    ("wallet import-hotkey", "'import-hotkey'"),
    ("wallet regen-hotkey", "'regen-hotkey'"),
    ("wallet list-hotkeys", "'list-hotkeys'"),
    ("wallet show-hotkey", "'show-hotkey'"),
    ("wallet show-address", "'show-address'"),
    ("wallet query-address", "'query-address'"),
    ("wallet register-hotkey", "'register-hotkey'"),
]

for label, pattern in cli_cmds:
    check(pattern in wallet_src, f"CLI: {label}")

# Check for subnet CLI commands
print("\n## 5. CLI COMMANDS — Subnet Operations")

# Check if there are subnet-specific CLI commands
subnet_cli_cmds = [
    "subnet create",
    "subnet list",
    "subnet register",
    "subnet set-weights",
    "subnet metagraph",
    "subnet delegate",
    "subnet claim",
]

# Check if subnet commands exist
subnet_cli_exists = os.path.exists("sdk/cli/commands/subnet.py")
check(
    subnet_cli_exists,
    "CLI: subnet command group",
    "sdk/cli/commands/subnet.py missing — no CLI for subnet ops!",
)
if not subnet_cli_exists:
    for cmd in subnet_cli_cmds:
        check(False, f"CLI: {cmd}", "no subnet CLI module")

# ══════════════════════════════════════════════════════════
# 6. KEY MANAGEMENT — keymanager module
# ══════════════════════════════════════════════════════════
print("\n## 6. KEY MANAGEMENT")

keymanager_files = [
    "sdk/keymanager/__init__.py",
    "sdk/keymanager/key_generator.py",
    "sdk/keymanager/encryption.py",
    "sdk/keymanager/transaction_signer.py",
]
for f in keymanager_files:
    check(os.path.exists(f), f"keymanager/{os.path.basename(f)}")

# ══════════════════════════════════════════════════════════
# 7. CONFIG — network configs
# ══════════════════════════════════════════════════════════
print("\n## 7. NETWORK CONFIG")

with open("sdk/polkadot/config.py") as f:
    config_src = f.read()

networks = ["polkadot_testnet", "polkadot_mainnet", "paseo_testnet", "local"]
for net in networks:
    check(net in config_src, f"Network: {net}")

# CLI config
with open("sdk/cli/config.py") as f:
    cli_config = f.read()
check(
    "polkadot" in cli_config.lower() or "westend" in cli_config.lower(),
    "CLI config references Polkadot",
    "CLI config may still reference L1",
)

# ══════════════════════════════════════════════════════════
# 8. DEMO SCRIPT — covers subnet flow
# ══════════════════════════════════════════════════════════
print("\n## 8. DEMO SCRIPT")

with open("demo_polkadot.py") as f:
    demo_src = f.read()

demo_checks = [
    ("token flow", "token"),
    ("staking flow", "staking"),
    ("oracle flow", "oracle"),
    ("training flow", "training"),
    ("zkml flow", "zkml"),
    ("escrow flow", "escrow"),
    ("subnet flow", "subnet"),
]
for label, keyword in demo_checks:
    check(keyword in demo_src, f"Demo: {label}")

# ══════════════════════════════════════════════════════════
# 9. DEPLOY SCRIPT
# ══════════════════════════════════════════════════════════
print("\n## 9. DEPLOY SCRIPT")

with open("luxtensor/contracts/scripts/deploy-polkadot.js") as f:
    deploy_src = f.read()

deploy_checks = [
    "MDTToken",
    "MDTVesting",
    "MDTStaking",
    "SubnetRegistry",
    "GradientAggregator",
    "TrainingEscrow",
    "AIOracle",
    "ZkMLVerifier",
    "PaymentEscrow",
    "createSubnet",  # creates demo subnet
    "fundEmissionPool",  # funds emission
]
for item in deploy_checks:
    check(item in deploy_src, f"Deploy: {item}")

# ══════════════════════════════════════════════════════════
# 10. AI/ML MODULES — check key classes exist
# ══════════════════════════════════════════════════════════
print("\n## 10. AI/ML MODULES")

ai_imports = [
    ("sdk.ai_ml.scoring", ["ConsensusAggregator", "AdvancedScorer"]),
    ("sdk.ai_ml.agent", ["ValidatorAIAgent", "MinerAIAgent"]),
]

for module_path, classes in ai_imports:
    mod_file = module_path.replace(".", "/") + "/__init__.py"
    if os.path.exists(mod_file):
        with open(mod_file) as f:
            content = f.read()
        for cls in classes:
            check(cls in content, f"{module_path}.{cls}")
    else:
        for cls in classes:
            check(False, f"{module_path}.{cls}", "module __init__.py missing")

# ══════════════════════════════════════════════════════════
# 11. REMAINING L1/LEGACY REFERENCES
# ══════════════════════════════════════════════════════════
print("\n## 11. LEGACY CLEANUP CHECK")

import subprocess

# Check for dead imports
dead_imports = ["sdk.luxtensor_pallets", "sdk.client.LuxtensorClient", "from sdk.client import"]
for dead in dead_imports:
    r = subprocess.run(["grep", "-rl", dead, "sdk/"], capture_output=True, text=True)
    files = [f for f in r.stdout.strip().split("\n") if f and "__pycache__" not in f]
    check(len(files) == 0, f"No refs to '{dead}'", f"found in: {', '.join(files)}" if files else "")

# ══════════════════════════════════════════════════════════
# 12. POLKADOT __init__.py EXPORTS
# ══════════════════════════════════════════════════════════
print("\n## 12. SDK EXPORTS")

with open("sdk/polkadot/__init__.py") as f:
    polkadot_init = f.read()

exports = ["PolkadotClient", "NetworkConfig", "NETWORKS"]
for exp in exports:
    check(exp in polkadot_init, f"sdk.polkadot exports {exp}")

# Check if SubnetClient is exported
check(
    "SubnetClient" in polkadot_init,
    "sdk.polkadot exports SubnetClient",
    "SubnetClient not exported from polkadot package",
)

# ══════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("AUDIT SUMMARY")
print("=" * 70)

if gaps:
    print(f"\n  GAPS FOUND: {len(gaps)}")
    print("  " + "-" * 60)
    for i, (label, detail) in enumerate(gaps, 1):
        print(f"  {i:2d}. {label}")
        if detail:
            print(f"      → {detail}")
else:
    print("\n  ALL FEATURES COMPLETE!")

print("\n" + "=" * 70)
