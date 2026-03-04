"""
Contract ABI loader for ModernTensor smart contracts on Polkadot Hub.

Provides easy access to compiled contract ABIs for web3.py interaction.
"""

import json
from pathlib import Path
from typing import Any

_ABI_DIR = Path(__file__).parent / "abis"

_ABI_CACHE: dict[str, list[dict[str, Any]]] = {}

# All deployed contract names
CONTRACT_NAMES = [
    "MDTToken",
    "MDTVesting",
    "MDTStaking",
    "ZkMLVerifier",
    "AIOracle",
    "SubnetRegistry",
    "GradientAggregator",
    "TrainingEscrow",
]


def get_abi(contract_name: str) -> list[dict[str, Any]]:
    """
    Load ABI for a contract by name.

    Args:
        contract_name: One of CONTRACT_NAMES (e.g. 'MDTToken', 'AIOracle')

    Returns:
        List of ABI entries

    Raises:
        FileNotFoundError: If ABI file doesn't exist
        ValueError: If contract name is unknown
    """
    if contract_name not in CONTRACT_NAMES:
        raise ValueError(
            f"Unknown contract '{contract_name}'. " f"Valid: {', '.join(CONTRACT_NAMES)}"
        )

    if contract_name not in _ABI_CACHE:
        abi_path = _ABI_DIR / f"{contract_name}.json"
        if not abi_path.exists():
            raise FileNotFoundError(
                f"ABI file not found: {abi_path}. "
                f"Run 'npx hardhat compile' in moderntensor/contracts/ first."
            )
        with open(abi_path) as f:
            _ABI_CACHE[contract_name] = json.load(f)

    return _ABI_CACHE[contract_name]


def get_all_abis() -> dict[str, list[dict[str, Any]]]:
    """Load all contract ABIs."""
    return {name: get_abi(name) for name in CONTRACT_NAMES}
