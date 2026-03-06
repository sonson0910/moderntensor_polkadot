"""
TrainingClient — GradientAggregator wrapper.

On-chain federated learning coordinator (FedAvg):
1. Owner creates a TrainingJob with model hash, rounds, and reward.
2. Participants submit gradient hashes each round.
3. Owner finalizes each round with the aggregated model hash.
4. After all rounds, participants claim proportional rewards.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING

from web3 import Web3

if TYPE_CHECKING:
    from .client import PolkadotClient


class JobStatus(IntEnum):
    """Training job status."""

    ACTIVE = 0
    COMPLETED = 1
    CANCELLED = 2


@dataclass
class TrainingJob:
    """Federated learning training job details."""

    model_hash: bytes
    total_rounds: int
    current_round: int
    reward_pool: int  # wei
    max_participants: int
    status: JobStatus
    creator: str

    @property
    def reward_pool_ether(self) -> float:
        return float(Web3.from_wei(self.reward_pool, "ether"))

    @property
    def is_active(self) -> bool:
        return self.status == JobStatus.ACTIVE

    @property
    def is_completed(self) -> bool:
        return self.status == JobStatus.COMPLETED

    @property
    def progress_pct(self) -> float:
        if self.total_rounds == 0:
            return 0.0
        return (self.current_round - 1) / self.total_rounds * 100


@dataclass
class GradientSubmission:
    """Gradient submission for a specific round."""

    gradient_hash: bytes
    data_size: int
    timestamp: int
    validated: bool


@dataclass
class RoundResult:
    """Finalized round result."""

    aggregated_hash: bytes
    participant_count: int
    total_data_size: int
    finalized_at: int


class TrainingClient:
    """GradientAggregator operations — federated learning on-chain."""

    def __init__(self, client: PolkadotClient) -> None:
        self._client = client
        self._contract = client._get_contract("GradientAggregator")

    # ── Read ────────────────────────────────────────────────

    def get_job_details(self, job_id: int) -> TrainingJob:
        """
        Get training job details.

        Args:
            job_id: Job identifier

        Returns:
            TrainingJob with full details
        """
        result = self._contract.functions.getJobDetails(job_id).call()
        return TrainingJob(
            model_hash=result[0],
            total_rounds=result[1],
            current_round=result[2],
            reward_pool=result[3],
            max_participants=result[4],
            status=JobStatus(result[5]),
            creator=result[6],
        )

    def get_submission(self, job_id: int, round_num: int, participant: str) -> GradientSubmission:
        """Get a participant's gradient submission for a round."""
        result = self._contract.functions.getSubmission(
            job_id, round_num, Web3.to_checksum_address(participant)
        ).call()
        return GradientSubmission(
            gradient_hash=result[0],
            data_size=result[1],
            timestamp=result[2],
            validated=result[3],
        )

    def get_round_participants(self, job_id: int, round_num: int) -> list[str]:
        """Get list of participants for a specific round."""
        return self._contract.functions.getRoundParticipants(job_id, round_num).call()

    def get_round_result(self, job_id: int, round_num: int) -> RoundResult:
        """Get finalized round result."""
        result = self._contract.functions.roundResults(job_id, round_num).call()
        return RoundResult(
            aggregated_hash=result[0],
            participant_count=result[1],
            total_data_size=result[2],
            finalized_at=result[3],
        )

    def get_participant_rounds(self, job_id: int, participant: str) -> int:
        """Get total validated rounds for a participant in a job."""
        return self._contract.functions.participantRounds(
            job_id, Web3.to_checksum_address(participant)
        ).call()

    def is_reward_claimed(self, job_id: int, participant: str) -> bool:
        """Check if reward has been claimed."""
        return self._contract.functions.rewardClaimed(
            job_id, Web3.to_checksum_address(participant)
        ).call()

    def next_job_id(self) -> int:
        """Get the next job ID (total jobs created)."""
        return self._contract.functions.nextJobId().call()

    # ── Write (Job Creator) ─────────────────────────────────

    def create_job(
        self,
        model_hash: bytes,
        total_rounds: int,
        reward_ether: float,
        max_participants: int = 10,
        round_deadline: int = 3600,
    ) -> str:
        """
        Create a new federated learning training job.

        Requires prior approve() of MDT tokens to GradientAggregator.

        Args:
            model_hash: 32-byte hash of initial model checkpoint
            total_rounds: Number of FedAvg rounds
            reward_ether: Total MDT reward (human-readable)
            max_participants: Max participants per round (default 10)
            round_deadline: Seconds per round (default 3600, min 60)

        Returns:
            Transaction hash

        Example:
            >>> model = Web3.keccak(text="resnet50-v1")
            >>> tx = client.training.create_job(model, total_rounds=5, reward_ether=100)
        """
        reward_wei = Web3.to_wei(reward_ether, "ether")
        tx = self._contract.functions.createJob(
            model_hash, total_rounds, reward_wei, max_participants, round_deadline
        ).build_transaction({})
        return self._client.send_tx(tx)

    def finalize_round(
        self,
        job_id: int,
        aggregated_hash: bytes,
        valid_participants: list[str],
    ) -> str:
        """
        Finalize the current round (job creator only).

        Args:
            job_id: Job identifier
            aggregated_hash: 32-byte FedAvg result hash
            valid_participants: Addresses of valid gradient submitters

        Returns:
            Transaction hash
        """
        addrs = [Web3.to_checksum_address(a) for a in valid_participants]
        tx = self._contract.functions.finalizeRound(
            job_id, aggregated_hash, addrs
        ).build_transaction({})
        return self._client.send_tx(tx)

    def cancel_job(self, job_id: int) -> str:
        """Cancel an active job and get refund (creator only)."""
        tx = self._contract.functions.cancelJob(job_id).build_transaction({})
        return self._client.send_tx(tx)

    # ── Write (Participant) ─────────────────────────────────

    def submit_gradient(
        self,
        job_id: int,
        gradient_hash: bytes,
        data_size: int,
    ) -> str:
        """
        Submit gradient hash for the current round.

        Args:
            job_id: Job identifier
            gradient_hash: 32-byte hash of gradient update
            data_size: Number of training samples used

        Returns:
            Transaction hash

        Example:
            >>> grad_hash = Web3.keccak(b"gradient_data...")
            >>> tx = client.training.submit_gradient(job_id=0, gradient_hash=grad_hash, data_size=1000)
        """
        tx = self._contract.functions.submitGradient(
            job_id, gradient_hash, data_size
        ).build_transaction({})
        return self._client.send_tx(tx)

    def claim_reward(self, job_id: int) -> str:
        """
        Claim proportional reward for a completed job.

        Reward = (my_validated_rounds / total_participant_rounds) * reward_pool

        Args:
            job_id: Completed job identifier

        Returns:
            Transaction hash
        """
        tx = self._contract.functions.claimReward(job_id).build_transaction({})
        return self._client.send_tx(tx)

    # ── Convenience ─────────────────────────────────────────

    def approve_and_create_job(
        self,
        model_hash: bytes,
        total_rounds: int,
        reward_ether: float,
        max_participants: int = 10,
        round_deadline: int = 3600,
    ) -> tuple[str, str]:
        """
        Approve MDT + create job in one call.

        Returns:
            Tuple of (approve_tx_hash, create_tx_hash)
        """
        reward_wei = Web3.to_wei(reward_ether, "ether")
        approve_hash = self._client.token.approve(self._contract.address, reward_wei)
        create_hash = self.create_job(
            model_hash, total_rounds, reward_ether, max_participants, round_deadline
        )
        return approve_hash, create_hash

    def __repr__(self) -> str:
        try:
            total = self.next_job_id()
            return f"TrainingClient(total_jobs={total})"
        except Exception:
            return "TrainingClient(not connected)"
