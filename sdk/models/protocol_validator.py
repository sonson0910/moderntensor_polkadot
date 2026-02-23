"""
Protocol Validator Model

Pydantic model for protocol validators matching the on-chain schema
from SubnetRegistry contract.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ProtocolValidator(BaseModel):
    """
    Validator info matching SubnetRegistry on-chain schema.

    SubnetRegistry returns:
    ```solidity
    struct Node {
        address hotkey;
        address coldkey;
        uint8 nodeType;    // 1 = Validator
        uint256 stake;
        uint256 delegatedStake;
        uint256 rank;
        uint256 incentive;
        uint256 emission;
        bool active;
    }
    ```
    """

    address: str = Field(
        ...,
        description="Validator address in 0x-prefixed hex format"
    )
    stake: int = Field(
        default=0,
        ge=0,
        description="Stake amount in base units (wei)"
    )
    stake_decimal: str = Field(
        default="0",
        description="Human-readable stake amount"
    )
    staked_at: int = Field(
        default=0,
        ge=0,
        description="Unix timestamp when stake was made"
    )
    is_validator: bool = Field(
        default=False,
        description="Whether stake meets minimum validator threshold"
    )

    # Protocol-specific fields
    activation_epoch: Optional[int] = Field(
        default=None,
        ge=0,
        description="Epoch when validator becomes eligible (epoch delay)"
    )
    active: bool = Field(
        default=True,
        description="Whether the validator is currently active"
    )
    rewards: int = Field(
        default=0,
        ge=0,
        description="Accumulated rewards in base units"
    )
    last_active_slot: int = Field(
        default=0,
        ge=0,
        description="Last slot this validator was active"
    )

    @field_validator('address')
    @classmethod
    def validate_address(cls, v: str) -> str:
        """Ensure address is properly formatted."""
        if not v.startswith('0x'):
            v = f'0x{v}'
        if len(v) != 42:  # 0x + 40 hex chars
            raise ValueError(f"Invalid address length: {len(v)}, expected 42")
        return v.lower()

    @classmethod
    def from_rpc_response(cls, data: dict) -> "ProtocolValidator":
        """
        Create from RPC/contract response.

        Handles both hex and decimal stake formats.
        """
        address = data.get("address", "0x" + "0" * 40)

        # Parse stake (hex or decimal)
        stake_raw = data.get("stake", "0")
        if isinstance(stake_raw, str) and stake_raw.startswith("0x"):
            stake = int(stake_raw, 16)
        else:
            stake = int(stake_raw) if stake_raw else 0

        return cls(
            address=address,
            stake=stake,
            stake_decimal=data.get("stakeDecimal", str(stake)),
            staked_at=data.get("stakedAt", 0),
            is_validator=data.get("isValidator", False),
            activation_epoch=data.get("activationEpoch"),
            active=data.get("active", True),
            rewards=data.get("rewards", 0),
            last_active_slot=data.get("lastActiveSlot", 0),
        )

    def to_rpc_format(self) -> dict:
        """Convert to RPC-compatible format."""
        return {
            "address": self.address,
            "stake": f"0x{self.stake:x}",
            "stakeDecimal": self.stake_decimal,
            "stakedAt": self.staked_at,
            "isValidator": self.is_validator,
        }

    @property
    def stake_mdt(self) -> float:
        """Get stake in MDT tokens (18 decimals)."""
        return self.stake / 10**18


# Backwards compatibility aliases
ModernTensorValidator = ProtocolValidator


class ProtocolValidatorSet(BaseModel):
    """Collection of validators from contract response."""

    validators: list[ProtocolValidator] = Field(default_factory=list)
    count: int = Field(default=0)

    @classmethod
    def from_rpc_response(cls, data: dict) -> "ProtocolValidatorSet":
        """Create from getMetagraph validators response."""
        validators_data = data.get("validators", [])
        validators = [
            ProtocolValidator.from_rpc_response(v)
            for v in validators_data
        ]
        return cls(
            validators=validators,
            count=data.get("count", len(validators))
        )

    @property
    def total_stake(self) -> int:
        """Get total stake across all validators."""
        return sum(v.stake for v in self.validators)

    @property
    def active_validators(self) -> list[ProtocolValidator]:
        """Get only active validators."""
        return [v for v in self.validators if v.active]


# Backwards compatibility alias
ModernTensorValidatorSet = ProtocolValidatorSet
