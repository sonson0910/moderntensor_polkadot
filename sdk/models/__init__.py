"""
ModernTensor SDK Data Models

Pydantic models for AI/ML subnet operations.
"""

from .subnet import (
    SubnetInfo,
    SubnetHyperparameters,
    RootConfig,
    RootValidatorInfo,
    SubnetWeights,
    EmissionShare,
    SubnetRegistrationResult,
)
from .validator import ValidatorInfo
from .miner import MinerInfo
from .protocol_validator import (
    ProtocolValidator, ProtocolValidatorSet,
    ModernTensorValidator, ModernTensorValidatorSet,  # backwards compat
)
from .protocol_miner import (
    ProtocolMiner, ProtocolMinerSet,
    ModernTensorMiner, ModernTensorMinerSet,  # backwards compat
)

__all__ = [
    "SubnetInfo",
    "SubnetHyperparameters",
    "ValidatorInfo",
    "MinerInfo",
    "RootConfig",
    "RootValidatorInfo",
    "SubnetWeights",
    "EmissionShare",
    "SubnetRegistrationResult",
    "ProtocolValidator",
    "ProtocolValidatorSet",
    "ProtocolMiner",
    "ProtocolMinerSet",
    # Backwards compatibility
    "ModernTensorValidator",
    "ModernTensorValidatorSet",
    "ModernTensorMiner",
    "ModernTensorMinerSet",
]
