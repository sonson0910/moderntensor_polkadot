"""
StakingClient — MDTStaking wrapper.

On-chain consensus economics via time-locked staking:
- 30+ days → 10% bonus
- 90+ days → 25% bonus
- 180+ days → 50% bonus
- 365+ days → 100% bonus
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from web3 import Web3

if TYPE_CHECKING:
    from .client import PolkadotClient


@dataclass
class StakeInfo:
    """Aggregate staking info for an address."""
    active_stakes: int
    total_locked: int  # wei
    pending_bonus: int  # wei

    @property
    def total_locked_ether(self) -> float:
        return float(Web3.from_wei(self.total_locked, "ether"))

    @property
    def pending_bonus_ether(self) -> float:
        return float(Web3.from_wei(self.pending_bonus, "ether"))


@dataclass
class StakeLock:
    """Individual stake lock details."""
    amount: int  # wei
    lock_time: int  # unix timestamp
    unlock_time: int  # unix timestamp
    bonus_rate: int  # basis points (1000 = 10%)
    withdrawn: bool
    can_unlock: bool

    @property
    def amount_ether(self) -> float:
        return float(Web3.from_wei(self.amount, "ether"))

    @property
    def bonus_percent(self) -> float:
        return self.bonus_rate / 100.0


class StakingClient:
    """MDTStaking operations — time-lock staking with bonuses."""

    def __init__(self, client: PolkadotClient) -> None:
        self._client = client
        self._contract = client._get_contract("MDTStaking")

    # ── Read ────────────────────────────────────────────────

    def get_bonus_rate(self, lock_days: int) -> int:
        """
        Preview bonus rate for a lock duration.

        Returns:
            Bonus in basis points (1000 = 10%, 10000 = 100%)
        """
        return self._contract.functions.getBonusRate(lock_days).call()

    def get_stake_info(self, address: Optional[str] = None) -> StakeInfo:
        """Get aggregate staking info."""
        addr = address or self._client.address
        result = self._contract.functions.getStakeInfo(
            Web3.to_checksum_address(addr)
        ).call()
        return StakeInfo(
            active_stakes=result[0],
            total_locked=result[1],
            pending_bonus=result[2],
        )

    def get_stake_lock(
        self, index: int, address: Optional[str] = None
    ) -> StakeLock:
        """Get details of a specific stake lock."""
        addr = address or self._client.address
        result = self._contract.functions.getStakeLock(
            Web3.to_checksum_address(addr), index
        ).call()
        return StakeLock(
            amount=result[0],
            lock_time=result[1],
            unlock_time=result[2],
            bonus_rate=result[3],
            withdrawn=result[4],
            can_unlock=result[5],
        )

    def get_stake_count(self, address: Optional[str] = None) -> int:
        """Get number of stake locks for an address."""
        addr = address or self._client.address
        return self._contract.functions.getStakeCount(
            Web3.to_checksum_address(addr)
        ).call()

    def total_staked(self) -> int:
        """Total MDT staked across all users (wei)."""
        return self._contract.functions.totalStaked().call()

    def total_bonus_paid(self) -> int:
        """Total bonus tokens paid out (wei)."""
        return self._contract.functions.totalBonusPaid().call()

    def bonus_pool_balance(self) -> int:
        """Available bonus pool tokens (contract balance minus staked principal).

        If this is less than pending bonuses, unlock() may revert.

        Returns:
            Available bonus tokens in wei
        """
        contract_balance = self._client.token.balance_of(self._contract.address)
        return contract_balance - self.total_staked()

    def bonus_pool_balance_ether(self) -> float:
        """Available bonus pool in ether units."""
        return float(Web3.from_wei(self.bonus_pool_balance(), "ether"))

    # ── Write ───────────────────────────────────────────────

    def lock(self, amount_ether: float, lock_days: int) -> str:
        """
        Lock MDT tokens for staking.

        Requires prior approve() to MDTStaking contract.

        Args:
            amount_ether: Amount of MDT to stake (human-readable)
            lock_days: Lock duration (1-365 days)

        Returns:
            Transaction hash

        Example:
            >>> client.staking.lock(amount_ether=100, lock_days=90)  # 25% bonus
        """
        amount_wei = Web3.to_wei(amount_ether, "ether")
        tx = self._contract.functions.lock(
            amount_wei, lock_days
        ).build_transaction({})
        return self._client.send_tx(tx)

    def unlock(self, index: int) -> str:
        """
        Unlock and withdraw staked tokens with bonus.

        Args:
            index: Stake lock index

        Returns:
            Transaction hash
        """
        tx = self._contract.functions.unlock(index).build_transaction({})
        return self._client.send_tx(tx)

    def fund_bonus_pool(self, amount_ether: float) -> str:
        """Fund the staking bonus pool (owner only)."""
        amount_wei = Web3.to_wei(amount_ether, "ether")
        tx = self._contract.functions.fundBonusPool(
            amount_wei
        ).build_transaction({})
        return self._client.send_tx(tx)

    # ── Convenience ─────────────────────────────────────────

    def approve_and_lock(self, amount_ether: float, lock_days: int) -> tuple[str, str]:
        """
        Approve + lock in one call.

        Returns:
            Tuple of (approve_tx_hash, lock_tx_hash)
        """
        amount_wei = Web3.to_wei(amount_ether, "ether")
        staking_address = self._contract.address
        approve_hash = self._client.token.approve(staking_address, amount_wei)
        lock_hash = self.lock(amount_ether, lock_days)
        return approve_hash, lock_hash

    def get_all_stakes(
        self, address: Optional[str] = None
    ) -> list[StakeLock]:
        """Get all stake locks for an address."""
        count = self.get_stake_count(address)
        return [self.get_stake_lock(i, address) for i in range(count)]

    def __repr__(self) -> str:
        try:
            total = Web3.from_wei(self.total_staked(), "ether")
            return f"StakingClient(total_staked={total:.2f} MDT)"
        except Exception:
            return "StakingClient(not connected)"
