"""
ZkMLClient — ZkMLVerifier wrapper.

On-chain verification of zkML proofs:
- STARK: Full RISC Zero STARK verification (via precompile)
- Groth16: SNARK-wrapped proofs (smaller, faster)
- Dev: Development mode (hash-based, for testing)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from web3 import Web3

if TYPE_CHECKING:
    from .client import PolkadotClient


# Proof type constants
PROOF_TYPE_STARK = 0
PROOF_TYPE_GROTH16 = 1
PROOF_TYPE_DEV = 2


@dataclass
class VerifiedProof:
    """Result of a verified proof."""
    proof_hash: bytes
    image_id: bytes
    verifier: str
    verified_at: int  # timestamp
    is_valid: bool


class ZkMLClient:
    """ZkMLVerifier operations — on-chain proof verification."""

    def __init__(self, client: PolkadotClient) -> None:
        self._client = client
        self._contract = client._get_contract("ZkMLVerifier")

    # ── Read ────────────────────────────────────────────────

    def is_image_trusted(self, image_id: bytes) -> bool:
        """Check if a zkML image ID is trusted."""
        return self._contract.functions.isImageTrusted(image_id).call()

    def get_verification(self, proof_hash: bytes) -> VerifiedProof:
        """Get verification result for a proof hash."""
        result = self._contract.functions.getVerification(proof_hash).call()
        return VerifiedProof(
            proof_hash=result[0],
            image_id=result[1],
            verifier=result[2],
            verified_at=result[3],
            is_valid=result[4],
        )

    def dev_mode_enabled(self) -> bool:
        """Check if dev mode is enabled."""
        return self._contract.functions.devModeEnabled().call()

    # ── Write ───────────────────────────────────────────────

    def verify(self, proof_data: bytes) -> str:
        """
        Verify a zkML proof (auto-detect type from encoded data).

        Args:
            proof_data: ABI-encoded proof data

        Returns:
            Transaction hash
        """
        tx = self._contract.functions.verify(proof_data).build_transaction({})
        return self._client.send_tx(tx)

    def verify_proof(
        self,
        image_id: bytes,
        journal: bytes,
        seal: bytes,
        proof_type: int = PROOF_TYPE_DEV,
    ) -> str:
        """
        Verify a zkML proof with explicit parameters.

        Args:
            image_id: 32-byte RISC Zero image ID
            journal: Public journal output
            seal: Proof seal data
            proof_type: PROOF_TYPE_STARK, PROOF_TYPE_GROTH16, or PROOF_TYPE_DEV

        Returns:
            Transaction hash
        """
        tx = self._contract.functions.verifyProof(
            image_id, journal, seal, proof_type
        ).build_transaction({})
        return self._client.send_tx(tx)

    # Backward-compat alias (deprecated)
    verify_full = verify_proof

    # ── Admin ───────────────────────────────────────────────

    def trust_image(self, image_id: bytes) -> str:
        """Trust a zkML image ID (owner only)."""
        tx = self._contract.functions.trustImage(
            image_id
        ).build_transaction({})
        return self._client.send_tx(tx)

    def batch_trust_images(self, image_ids: list[bytes]) -> str:
        """Trust multiple image IDs at once (owner only)."""
        tx = self._contract.functions.trustImages(
            image_ids
        ).build_transaction({})
        return self._client.send_tx(tx)

    def set_dev_mode(self, enabled: bool) -> str:
        """Toggle dev mode (owner only)."""
        tx = self._contract.functions.setDevMode(
            enabled
        ).build_transaction({})
        return self._client.send_tx(tx)

    # ── Convenience (Dev Mode) ──────────────────────────────

    def create_dev_proof(
        self, image_id: bytes, journal: bytes
    ) -> tuple[bytes, bytes]:
        """
        Create a dev mode proof (for testing).

        Dev proof seal = keccak256(imageId || journal)

        Returns:
            Tuple of (seal, proof_hash)
        """
        seal = Web3.keccak(image_id + journal)
        proof_hash = Web3.keccak(image_id + journal + seal)
        return seal, proof_hash

    def __repr__(self) -> str:
        try:
            dev = "dev" if self.dev_mode_enabled() else "prod"
            return f"ZkMLClient(mode={dev})"
        except Exception:
            return "ZkMLClient(not connected)"
