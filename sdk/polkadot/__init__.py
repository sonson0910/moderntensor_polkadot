"""
ModernTensor Polkadot Hub Client

Python SDK for interacting with ModernTensor smart contracts
deployed on Polkadot Hub via pallet-revive EVM.
"""

from .client import PolkadotClient
from .config import NetworkConfig, NETWORKS, load_deployment
from .subnet import SubnetClient
from .training import TrainingClient
from .escrow import EscrowClient
from .llm_adapter import LocalLLMAdapter
from .ipfs_client import IPFSClient

__all__ = [
    "PolkadotClient",
    "SubnetClient",
    "TrainingClient",
    "EscrowClient",
    "NetworkConfig",
    "NETWORKS",
    "load_deployment",
    "LocalLLMAdapter",
    "IPFSClient",
]
