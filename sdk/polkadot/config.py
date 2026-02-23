"""
Network configuration and deployment loader for Polkadot Hub.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class NetworkConfig:
    """Polkadot Hub network configuration."""
    name: str
    rpc_url: str
    chain_id: int
    explorer_url: Optional[str] = None
    ws_url: Optional[str] = None


# Pre-configured Polkadot Hub networks
NETWORKS: dict[str, NetworkConfig] = {
    "polkadot_mainnet": NetworkConfig(
        name="polkadot_mainnet",
        rpc_url="https://asset-hub-eth-rpc.polkadot.io",
        chain_id=420420420,
        explorer_url="https://assethub-polkadot.subscan.io",
    ),
    # Official Polkadot Hub TestNet (Paseo-based) — from docs.polkadot.com
    "polkadot_testnet": NetworkConfig(
        name="polkadot_testnet",
        rpc_url="https://services.polkadothub-rpc.com/testnet",
        chain_id=420420417,
        explorer_url="https://blockscout-westend.parity.io",
    ),
    # Alias for polkadot_testnet
    "polkadot_hub_testnet": NetworkConfig(
        name="polkadot_hub_testnet",
        rpc_url="https://services.polkadothub-rpc.com/testnet",
        chain_id=420420417,
        explorer_url="https://blockscout-westend.parity.io",
    ),
    # Legacy: Westend AssetHub (requires resolc PolkaVM compiler)
    "westend": NetworkConfig(
        name="westend",
        rpc_url="https://westend-asset-hub-eth-rpc.polkadot.io",
        chain_id=420420421,
        explorer_url="https://assethub-westend.subscan.io",
    ),
    "paseo_testnet": NetworkConfig(
        name="paseo_testnet",
        rpc_url="https://testnet-paseo-asset-hub-eth-rpc.polkadot.io",
        chain_id=420420422,
    ),
    "local": NetworkConfig(
        name="local",
        rpc_url="http://localhost:8545",
        chain_id=1337,
    ),
}


def load_deployment(
    path: Optional[str] = None,
    network: str = "polkadot_testnet",
) -> dict[str, Any]:
    """
    Load deployment addresses from deployments-polkadot.json.

    Args:
        path: Explicit path to deployment JSON. If None, auto-detect.
        network: Network name for auto-detection.

    Returns:
        Dict with contract name -> address mapping.
    """
    if path is None:
        # Look for deployment file relative to contracts dir
        candidates = [
            Path("luxtensor/contracts/deployments-polkadot.json"),
            Path("deployments-polkadot.json"),
            Path.home() / ".moderntensor" / f"deployments-{network}.json",
        ]
        for candidate in candidates:
            if candidate.exists():
                path = str(candidate)
                break

    if path is None:
        raise FileNotFoundError(
            "No deployment file found. Run deploy-polkadot.js first.\n"
            "  npx hardhat run scripts/deploy-polkadot.js --network polkadot_testnet"
        )

    with open(path) as f:
        data = json.load(f)

    # Extract addresses from deployment data
    addresses = {}
    if "contracts" in data:
        for name, info in data["contracts"].items():
            addresses[name] = info if isinstance(info, str) else info.get("address", "")
    else:
        addresses = data

    return addresses
