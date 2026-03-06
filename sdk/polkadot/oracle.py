"""
OracleClient — AIOracle wrapper.

Flow:
1. User calls request_ai() with payment → creates AI request
2. Off-chain miners listen for requests via events
3. Miners process and call fulfill_request() with result + proof
4. Payment is released to miner minus protocol fee
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING

from web3 import Web3

if TYPE_CHECKING:
    from .client import PolkadotClient


class RequestStatus(IntEnum):
    """AI request status."""

    PENDING = 0
    FULFILLED = 1
    CANCELLED = 2
    EXPIRED = 3


@dataclass
class AIRequest:
    """AI request details."""

    requester: str
    model_hash: bytes
    input_data: bytes
    reward: int  # wei
    created_at: int  # block number
    deadline: int  # block number
    status: RequestStatus
    result: bytes
    fulfiller: str
    proof_hash: bytes

    @property
    def reward_ether(self) -> float:
        return float(Web3.from_wei(self.reward, "ether"))

    @property
    def is_pending(self) -> bool:
        return self.status == RequestStatus.PENDING

    @property
    def is_fulfilled(self) -> bool:
        return self.status == RequestStatus.FULFILLED


class OracleClient:
    """AIOracle operations — decentralized AI inference."""

    def __init__(self, client: PolkadotClient) -> None:
        self._client = client
        self._contract = client._get_contract("AIOracle")

    # ── Read ────────────────────────────────────────────────

    def get_request(self, request_id: bytes) -> AIRequest:
        """
        Get AI request details.

        Args:
            request_id: 32-byte request identifier

        Returns:
            AIRequest with full details
        """
        result = self._contract.functions.getRequest(request_id).call()
        return AIRequest(
            requester=result[0],
            model_hash=result[1],
            input_data=result[2],
            reward=result[3],
            created_at=result[4],
            deadline=result[5],
            status=RequestStatus(result[6]),
            result=result[7],
            fulfiller=result[8],
            proof_hash=result[9],
        )

    def is_model_approved(self, model_hash: bytes) -> bool:
        """Check if a model is approved for inference."""
        return self._contract.functions.isModelApproved(model_hash).call()

    def protocol_fee_bps(self) -> int:
        """Get protocol fee in basis points."""
        return self._contract.functions.protocolFeeBps().call()

    def total_requests(self) -> int:
        """Total number of AI requests made."""
        return self._contract.functions.requestCount().call()

    # ── Write (User) ────────────────────────────────────────

    def request_ai(
        self,
        model_hash: bytes,
        input_data: bytes,
        timeout: int = 0,
        payment_ether: float = 0.01,
    ) -> str:
        """
        Submit an AI inference request with payment.

        Args:
            model_hash: 32-byte model identifier
            input_data: Encoded input data
            timeout: Custom timeout in blocks (0 = default)
            payment_ether: Payment amount in native token

        Returns:
            Transaction hash

        Example:
            >>> model = Web3.keccak(text="gpt-4-turbo")
            >>> tx = client.oracle.request_ai(model, b"Hello, AI!", payment_ether=0.1)
        """
        payment_wei = Web3.to_wei(payment_ether, "ether")
        tx = self._contract.functions.requestAI(model_hash, input_data, timeout).build_transaction(
            {"value": payment_wei}
        )
        return self._client.send_tx(tx)

    def cancel_request(self, request_id: bytes) -> str:
        """Cancel pending request and get refund."""
        tx = self._contract.functions.cancelRequest(request_id).build_transaction({})
        return self._client.send_tx(tx)

    # ── Write (Miner) ──────────────────────────────────────

    def fulfill_request(
        self,
        request_id: bytes,
        result: bytes,
        proof_hash: bytes = b"\x00" * 32,
    ) -> str:
        """
        Fulfill an AI request (miners only).

        Args:
            request_id: Request to fulfill
            result: AI output data
            proof_hash: zkML proof hash (optional)

        Returns:
            Transaction hash
        """
        tx = self._contract.functions.fulfillRequest(
            request_id, result, proof_hash
        ).build_transaction({})
        return self._client.send_tx(tx)

    def mark_expired(self, request_id: bytes) -> str:
        """Mark an expired request for refund."""
        tx = self._contract.functions.markExpired(request_id).build_transaction({})
        return self._client.send_tx(tx)

    # ── Admin ───────────────────────────────────────────────

    def approve_model(self, model_hash: bytes) -> str:
        """Approve a model for inference (owner only)."""
        tx = self._contract.functions.approveModel(model_hash).build_transaction({})
        return self._client.send_tx(tx)

    def set_zkml_verifier(self, verifier_address: str) -> str:
        """Set ZkMLVerifier contract (owner only)."""
        tx = self._contract.functions.setZkMLVerifier(
            Web3.to_checksum_address(verifier_address)
        ).build_transaction({})
        return self._client.send_tx(tx)

    def set_protocol_fee(self, fee_bps: int) -> str:
        """Set protocol fee in basis points (owner only, max 1000 = 10%)."""
        tx = self._contract.functions.setProtocolFee(fee_bps).build_transaction({})
        return self._client.send_tx(tx)

    def register_fulfiller(self, fulfiller: str) -> str:
        """
        Register an address as an authorized fulfiller (owner only).

        Fulfillers MUST be registered before calling fulfill_request().
        The contract requires registeredFulfillers[msg.sender] == true.

        Args:
            fulfiller: Address to authorize as fulfiller

        Returns:
            Transaction hash
        """
        tx = self._contract.functions.registerFulfiller(
            Web3.to_checksum_address(fulfiller)
        ).build_transaction({})
        return self._client.send_tx(tx)

    def revoke_fulfiller(self, fulfiller: str) -> str:
        """Revoke fulfiller authorization (owner only)."""
        tx = self._contract.functions.revokeFulfiller(
            Web3.to_checksum_address(fulfiller)
        ).build_transaction({})
        return self._client.send_tx(tx)

    def revoke_model(self, model_hash: bytes) -> str:
        """Revoke a previously approved model (owner only)."""
        tx = self._contract.functions.revokeModel(model_hash).build_transaction({})
        return self._client.send_tx(tx)

    def set_default_timeout(self, timeout: int) -> str:
        """Set the default timeout for AI requests in blocks (owner only)."""
        tx = self._contract.functions.setDefaultTimeout(timeout).build_transaction({})
        return self._client.send_tx(tx)

    def withdraw_fees(self) -> str:
        """Withdraw accumulated protocol fees (owner only)."""
        tx = self._contract.functions.withdrawFees().build_transaction({})
        return self._client.send_tx(tx)

    def get_result(self, request_id: bytes) -> bytes:
        """
        Get the result data of a fulfilled request.

        Args:
            request_id: 32-byte request identifier

        Returns:
            Result bytes (empty if not yet fulfilled)
        """
        return self._contract.functions.getResult(request_id).call()

    def __repr__(self) -> str:
        try:
            total = self.total_requests()
            return f"OracleClient(total_requests={total})"
        except Exception:
            return "OracleClient(not connected)"
