"""
EscrowClient — TrainingEscrow wrapper.

Stake-gated training escrow with slashing:
1. Task creator deposits MDT rewards into escrow.
2. Trainers stake MDT to join a task.
3. Trainers submit result hashes after training.
4. Owner/verifier validates results — invalid submissions are slashed.
5. Validated trainers claim proportional reward + stake return.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING

from web3 import Web3

if TYPE_CHECKING:
    from .client import PolkadotClient


class TaskStatus(IntEnum):
    """Training task status."""

    OPEN = 0
    IN_PROGRESS = 1
    COMPLETED = 2
    CANCELLED = 3


@dataclass
class TrainingTask:
    """Training task details."""

    creator: str
    model_hash: bytes
    reward_amount: int  # wei
    min_stake: int  # wei
    max_trainers: int
    deadline: int  # unix timestamp
    status: TaskStatus
    trainer_count: int

    @property
    def reward_ether(self) -> float:
        return float(Web3.from_wei(self.reward_amount, "ether"))

    @property
    def min_stake_ether(self) -> float:
        return float(Web3.from_wei(self.min_stake, "ether"))

    @property
    def is_open(self) -> bool:
        return self.status == TaskStatus.OPEN

    @property
    def is_in_progress(self) -> bool:
        return self.status == TaskStatus.IN_PROGRESS

    @property
    def is_completed(self) -> bool:
        return self.status == TaskStatus.COMPLETED

    @property
    def slots_available(self) -> int:
        return max(0, self.max_trainers - self.trainer_count)


@dataclass
class TrainerInfo:
    """Trainer participation details."""

    stake_amount: int  # wei
    submitted: bool
    validated: bool
    slashed: bool
    reward_claimed: bool
    result_hash: bytes
    submitted_at: int

    @property
    def stake_ether(self) -> float:
        return float(Web3.from_wei(self.stake_amount, "ether"))


class EscrowClient:
    """TrainingEscrow operations — stake-gated training with slashing."""

    def __init__(self, client: PolkadotClient) -> None:
        self._client = client
        self._contract = client._get_contract("TrainingEscrow")

    # ── Read ────────────────────────────────────────────────

    def get_task_details(self, task_id: int) -> TrainingTask:
        """
        Get training task details.

        Args:
            task_id: Task identifier

        Returns:
            TrainingTask with full details
        """
        result = self._contract.functions.getTaskDetails(task_id).call()
        return TrainingTask(
            creator=result[0],
            model_hash=result[1],
            reward_amount=result[2],
            min_stake=result[3],
            max_trainers=result[4],
            deadline=result[5],
            status=TaskStatus(result[6]),
            trainer_count=result[7],
        )

    def get_task_trainers(self, task_id: int) -> list[str]:
        """Get list of trainer addresses for a task."""
        return self._contract.functions.getTaskTrainers(task_id).call()

    def get_trainer_info(self, task_id: int, trainer: str) -> TrainerInfo:
        """Get a trainer's participation details."""
        result = self._contract.functions.trainers(
            task_id, Web3.to_checksum_address(trainer)
        ).call()
        return TrainerInfo(
            stake_amount=result[0],
            submitted=result[1],
            validated=result[2],
            slashed=result[3],
            reward_claimed=result[4],
            result_hash=result[5],
            submitted_at=result[6],
        )

    def next_task_id(self) -> int:
        """Get next task ID (total tasks created)."""
        return self._contract.functions.nextTaskId().call()

    def slash_rate(self) -> int:
        """Get slash rate in basis points (5000 = 50%)."""
        return self._contract.functions.slashRate().call()

    def slash_rate_pct(self) -> float:
        """Get slash rate as percentage."""
        return self.slash_rate() / 100.0

    def total_slashed(self) -> int:
        """Total MDT slashed across all tasks (wei)."""
        return self._contract.functions.totalSlashed().call()

    # ── Write (Task Creator) ────────────────────────────────

    def create_task(
        self,
        model_hash: bytes,
        reward_ether: float,
        min_stake_ether: float = 10.0,
        max_trainers: int = 5,
        duration_seconds: int = 86400,
    ) -> str:
        """
        Create a new training task with escrowed rewards.

        Requires prior approve() of MDT tokens to TrainingEscrow.

        Args:
            model_hash: 32-byte hash of model to train
            reward_ether: Total MDT reward (human-readable)
            min_stake_ether: Minimum stake per trainer (default 10 MDT)
            max_trainers: Maximum trainers (default 5)
            duration_seconds: Task duration (default 86400 = 24h, min 300)

        Returns:
            Transaction hash

        Example:
            >>> model = Web3.keccak(text="gpt-finetune-v1")
            >>> tx = client.escrow.create_task(model, reward_ether=50, min_stake_ether=5)
        """
        reward_wei = Web3.to_wei(reward_ether, "ether")
        min_stake_wei = Web3.to_wei(min_stake_ether, "ether")
        tx = self._contract.functions.createTask(
            model_hash, reward_wei, min_stake_wei, max_trainers, duration_seconds
        ).build_transaction({})
        return self._client.send_tx(tx)

    def cancel_task(self, task_id: int) -> str:
        """Cancel task and refund (creator only). Refunds trainer stakes too."""
        tx = self._contract.functions.cancelTask(task_id).build_transaction({})
        return self._client.send_tx(tx)

    # ── Write (Trainer) ─────────────────────────────────────

    def join_task(self, task_id: int, stake_ether: float) -> str:
        """
        Join a training task by staking MDT tokens.

        Requires prior approve() of MDT tokens to TrainingEscrow.

        Args:
            task_id: Task identifier
            stake_ether: Amount of MDT to stake (must be >= minStake)

        Returns:
            Transaction hash
        """
        stake_wei = Web3.to_wei(stake_ether, "ether")
        tx = self._contract.functions.joinTask(task_id, stake_wei).build_transaction({})
        return self._client.send_tx(tx)

    def submit_result(self, task_id: int, result_hash: bytes) -> str:
        """
        Submit training result hash.

        Args:
            task_id: Task identifier
            result_hash: 32-byte hash of training result

        Returns:
            Transaction hash
        """
        tx = self._contract.functions.submitResult(task_id, result_hash).build_transaction({})
        return self._client.send_tx(tx)

    def claim_reward(self, task_id: int) -> str:
        """
        Claim reward + stake for a completed task.

        Only for validated trainers after task completion.

        Returns:
            Transaction hash
        """
        tx = self._contract.functions.claimReward(task_id).build_transaction({})
        return self._client.send_tx(tx)

    # ── Write (Admin/Verifier) ──────────────────────────────

    def validate_trainer(self, task_id: int, trainer: str, is_valid: bool) -> str:
        """
        Validate a trainer's submission (owner only).

        Invalid trainers are slashed at the configured slash rate.

        Args:
            task_id: Task identifier
            trainer: Trainer address
            is_valid: Whether the submission is valid

        Returns:
            Transaction hash
        """
        tx = self._contract.functions.validateTrainer(
            task_id, Web3.to_checksum_address(trainer), is_valid
        ).build_transaction({})
        return self._client.send_tx(tx)

    def complete_task(self, task_id: int) -> str:
        """Mark a task as completed (owner only)."""
        tx = self._contract.functions.completeTask(task_id).build_transaction({})
        return self._client.send_tx(tx)

    def set_slash_rate(self, rate_bps: int) -> str:
        """Set slash rate in basis points (owner only, max 10000)."""
        tx = self._contract.functions.setSlashRate(rate_bps).build_transaction({})
        return self._client.send_tx(tx)

    def withdraw_slashed(self, to: str) -> str:
        """Withdraw slashed tokens to treasury (owner only)."""
        tx = self._contract.functions.withdrawSlashed(
            Web3.to_checksum_address(to)
        ).build_transaction({})
        return self._client.send_tx(tx)

    # ── Convenience ─────────────────────────────────────────

    def approve_and_create_task(
        self,
        model_hash: bytes,
        reward_ether: float,
        min_stake_ether: float = 10.0,
        max_trainers: int = 5,
        duration_seconds: int = 86400,
    ) -> tuple[str, str]:
        """
        Approve MDT + create task in one call.

        Returns:
            Tuple of (approve_tx_hash, create_tx_hash)
        """
        reward_wei = Web3.to_wei(reward_ether, "ether")
        approve_hash = self._client.token.approve(self._contract.address, reward_wei)
        create_hash = self.create_task(
            model_hash, reward_ether, min_stake_ether, max_trainers, duration_seconds
        )
        return approve_hash, create_hash

    def approve_and_join_task(self, task_id: int, stake_ether: float) -> tuple[str, str]:
        """
        Approve MDT + join task in one call.

        Returns:
            Tuple of (approve_tx_hash, join_tx_hash)
        """
        stake_wei = Web3.to_wei(stake_ether, "ether")
        approve_hash = self._client.token.approve(self._contract.address, stake_wei)
        join_hash = self.join_task(task_id, stake_ether)
        return approve_hash, join_hash

    def __repr__(self) -> str:
        try:
            total = self.next_task_id()
            slash = self.slash_rate_pct()
            return f"EscrowClient(total_tasks={total}, slash_rate={slash:.0f}%)"
        except Exception:
            return "EscrowClient(not connected)"
