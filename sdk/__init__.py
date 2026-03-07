"""
ModernTensor SDK

Python SDK for AI/ML model validation, scoring, and decentralized AI quality assurance.
Built for the Polkadot ecosystem via pallet-revive EVM compatibility.
"""

# Polkadot Hub Client (EVM interaction layer)
from .polkadot import PolkadotClient

# AI/ML Framework — available via submodule access:
# - sdk.ai_ml.agent    → AI agent framework
# - sdk.ai_ml.scoring  → Model scoring and evaluation
# - sdk.ai_ml.zkml     → Zero-knowledge ML proofs
# - sdk.ai_ml.subnets  → Subnet definitions
# - sdk.ai_ml.models   → ML model registry

# Utilities (BPS conversion, score distribution)
from .utils.bps_utils import (
    float_to_bps,
    bps_to_float,
    bps_to_percent,
    percent_to_bps,
    calculate_proportional_share,
    distribute_by_scores,
    validate_bps,
    MAX_BPS,
    BPS_PRECISION,
)

# Errors (structured RPC errors)
from .errors import (
    RpcError,
    RpcErrorCode,
    BlockNotFoundError,
    TransactionNotFoundError,
    InsufficientFundsError,
    InvalidSignatureError,
    NonceTooLowError,
    GasLimitExceededError,
    RateLimitedError,
    MempoolFullError,
    parse_rpc_error,
    check_rpc_response,
)

# Caching (core utilities)
from .core.cache import (
    ModernTensorCache,
    MemoryCache,
    RedisCache,
    CacheBackend,
    cached,
    get_cache,
    set_cache,
)

# Version
from .version import __version__


__all__ = [
    # Polkadot Client
    "PolkadotClient",
    # Utilities
    "float_to_bps",
    "bps_to_float",
    "bps_to_percent",
    "percent_to_bps",
    "calculate_proportional_share",
    "distribute_by_scores",
    "validate_bps",
    "MAX_BPS",
    "BPS_PRECISION",
    # Errors
    "RpcError",
    "RpcErrorCode",
    "BlockNotFoundError",
    "TransactionNotFoundError",
    "InsufficientFundsError",
    "InvalidSignatureError",
    "NonceTooLowError",
    "GasLimitExceededError",
    "RateLimitedError",
    "MempoolFullError",
    "parse_rpc_error",
    "check_rpc_response",
    # Caching
    "ModernTensorCache",
    "MemoryCache",
    "RedisCache",
    "CacheBackend",
    "cached",
    "get_cache",
    "set_cache",
    # Version
    "__version__",
]
