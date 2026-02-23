"""
ModernTensor Polkadot Hub Client

Python SDK for interacting with ModernTensor smart contracts
deployed on Polkadot Hub via pallet-revive EVM.
"""

from .client import PolkadotClient
from .config import NetworkConfig, NETWORKS, load_deployment
from .subnet import SubnetClient

__all__ = [
    "PolkadotClient",
    "SubnetClient",
    "NetworkConfig",
    "NETWORKS",
    "load_deployment",
]
