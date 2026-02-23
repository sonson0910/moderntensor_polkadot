"""
Protocol Miner Model

Pydantic model for protocol miners with BPS (Basis Points) score representation.

This matches the on-chain MinerInfo struct which uses `score_bps: u64` for
deterministic fixed-point arithmetic in consensus.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ProtocolMiner(BaseModel):
    """
    Miner info matching on-chain MinerInfo struct.

    On-chain definition (SubnetRegistry.sol):
    ```solidity
    struct Node {
        address hotkey;
        address coldkey;
        uint8 nodeType;  // 0=Miner, 1=Validator
        uint256 stake;
        uint256 rank;
    }
    ```

    BPS (Basis Points) ensures deterministic consensus by avoiding
    floating-point precision issues.
    """

    address: str = Field(
        ...,
        description="Miner address in 0x-prefixed hex format (20 bytes)"
    )
    score_bps: int = Field(
        default=0,
        ge=0,
        le=10000,
        description="Score in basis points (0-10000, where 10000 = 100%)"
    )

    # Optional fields for extended info
    active: bool = Field(
        default=True,
        description="Whether miner is currently active"
    )
    last_update: int = Field(
        default=0,
        ge=0,
        description="Block height of last update"
    )
    emission: int = Field(
        default=0,
        ge=0,
        description="Total emission received in base units"
    )

    @field_validator('address')
    @classmethod
    def validate_address(cls, v: str) -> str:
        """Ensure address is properly formatted."""
        if not v.startswith('0x'):
            v = f'0x{v}'
        if len(v) != 42:
            raise ValueError(f"Invalid address length: {len(v)}, expected 42")
        return v.lower()

    @property
    def score(self) -> float:
        """
        Get score as float (0.0 - 1.0) for backwards compatibility.

        Note: Use score_bps for consensus-critical operations to avoid
        floating-point precision issues.
        """
        return self.score_bps / 10000.0

    @property
    def score_percent(self) -> float:
        """Get score as percentage (0.0 - 100.0)."""
        return self.score_bps / 100.0

    @classmethod
    def from_float_score(
        cls,
        address: str,
        score: float,
        **kwargs
    ) -> "ProtocolMiner":
        """
        Factory method to create from float score.

        Args:
            address: Miner address
            score: Score as float (0.0 - 1.0)
            **kwargs: Additional fields

        Returns:
            ProtocolMiner instance

        Example:
            >>> miner = ProtocolMiner.from_float_score("0x1234...", 0.85)
            >>> miner.score_bps
            8500
        """
        if not 0.0 <= score <= 1.0:
            raise ValueError(f"Score must be between 0.0 and 1.0, got {score}")
        return cls(
            address=address,
            score_bps=int(score * 10000),
            **kwargs
        )

    @classmethod
    def from_bytes_address(
        cls,
        address_bytes: bytes,
        score_bps: int,
        **kwargs
    ) -> "ProtocolMiner":
        """
        Create from raw bytes address (matching EVM bytes20).

        Args:
            address_bytes: 20-byte address
            score_bps: Score in basis points
        """
        if len(address_bytes) != 20:
            raise ValueError(f"Address must be 20 bytes, got {len(address_bytes)}")
        address_hex = f"0x{address_bytes.hex()}"
        return cls(address=address_hex, score_bps=score_bps, **kwargs)

    def to_dict(self) -> dict:
        """Convert to dictionary with both BPS and float score."""
        return {
            "address": self.address,
            "score_bps": self.score_bps,
            "score": self.score,
            "active": self.active,
            "last_update": self.last_update,
            "emission": self.emission,
        }


# Backwards compatibility aliases
ModernTensorMiner = ProtocolMiner


class ProtocolMinerSet(BaseModel):
    """Collection of miners for batch operations."""

    miners: list[ProtocolMiner] = Field(default_factory=list)

    @property
    def total_score_bps(self) -> int:
        """Sum of all miner scores in BPS."""
        return sum(m.score_bps for m in self.miners)

    @property
    def active_miners(self) -> list[ProtocolMiner]:
        """Get only active miners."""
        return [m for m in self.miners if m.active]

    def get_by_address(self, address: str) -> Optional[ProtocolMiner]:
        """Find miner by address."""
        address = address.lower()
        for miner in self.miners:
            if miner.address.lower() == address:
                return miner
        return None

    def calculate_rewards(self, total_reward: int) -> dict[str, int]:
        """
        Calculate rewards proportional to scores.

        Args:
            total_reward: Total reward to distribute in base units

        Returns:
            Dict mapping address -> reward amount
        """
        if not self.miners:
            return {}

        total_bps = self.total_score_bps
        if total_bps == 0:
            share = total_reward // len(self.miners)
            return {m.address: share for m in self.miners}

        rewards = {}
        for miner in self.miners:
            reward = (total_reward * miner.score_bps) // total_bps
            rewards[miner.address] = reward

        return rewards


# Backwards compatibility alias
ModernTensorMinerSet = ProtocolMinerSet
