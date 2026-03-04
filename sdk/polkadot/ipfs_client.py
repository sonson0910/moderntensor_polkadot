"""
IPFSClient — Decentralized storage for AI inference outputs.

Pins large AI outputs to IPFS instead of storing on-chain,
significantly reducing gas costs. Only the CID (content identifier)
is stored on-chain for verification.

Backends:
- Pinata (free tier, reliable)
- Local IPFS node (ipfs daemon)
- Fallback: in-memory hash (for development/demo without IPFS)
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class IPFSClient:
    """
    Pin and retrieve AI inference outputs from IPFS.

    Usage:
        client = IPFSClient.auto_detect()
        cid = client.pin(b"AI model output data...")
        data = client.fetch(cid)
    """

    def __init__(
        self,
        backend: str = "auto",
        pinata_jwt: Optional[str] = None,
        ipfs_api_url: str = "http://localhost:5001",
    ) -> None:
        self.backend = backend
        self.pinata_jwt = pinata_jwt
        self.ipfs_api_url = ipfs_api_url
        self._local_cache: dict[str, bytes] = {}

        if backend == "auto":
            self.backend = self._detect_backend()

        logger.info("IPFSClient initialized: backend=%s", self.backend)

    def _detect_backend(self) -> str:
        """Auto-detect available IPFS backend."""
        # Try Pinata
        if self.pinata_jwt:
            return "pinata"
        # Try local IPFS node
        if self._check_local_ipfs():
            return "ipfs"
        # Fallback
        return "local_hash"

    def _check_local_ipfs(self) -> bool:
        """Check if local IPFS daemon is running."""
        try:
            import httpx
            resp = httpx.post(
                f"{self.ipfs_api_url}/api/v0/id",
                timeout=2,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def pin(self, data: bytes, name: str = "ai-output") -> str:
        """
        Pin data to IPFS.

        Args:
            data: Raw bytes to pin
            name: Optional filename for the pin

        Returns:
            CID (content identifier) string
        """
        if self.backend == "pinata":
            return self._pin_pinata(data, name)
        elif self.backend == "ipfs":
            return self._pin_local(data)
        else:
            return self._pin_local_hash(data)

    def fetch(self, cid: str) -> Optional[bytes]:
        """
        Fetch data from IPFS by CID.

        Args:
            cid: Content identifier

        Returns:
            Data bytes, or None if not found
        """
        # Try local cache first
        if cid in self._local_cache:
            return self._local_cache[cid]

        if self.backend == "pinata":
            return self._fetch_gateway(cid)
        elif self.backend == "ipfs":
            return self._fetch_local(cid)
        else:
            return self._local_cache.get(cid)

    def _pin_pinata(self, data: bytes, name: str) -> str:
        """Pin to Pinata (free tier)."""
        import httpx

        try:
            resp = httpx.post(
                "https://api.pinata.cloud/pinning/pinFileToIPFS",
                headers={"Authorization": f"Bearer {self.pinata_jwt}"},
                files={"file": (name, data)},
                data={"pinataMetadata": json.dumps({"name": name})},
                timeout=30,
            )
            resp.raise_for_status()
            cid = resp.json()["IpfsHash"]
            self._local_cache[cid] = data
            logger.info("Pinned to Pinata: %s (%d bytes)", cid, len(data))
            return cid

        except Exception as e:
            logger.warning("Pinata pin failed: %s, using local hash", e)
            return self._pin_local_hash(data)

    def _pin_local(self, data: bytes) -> str:
        """Pin to local IPFS node."""
        import httpx

        try:
            resp = httpx.post(
                f"{self.ipfs_api_url}/api/v0/add",
                files={"file": ("data", data)},
                timeout=10,
            )
            resp.raise_for_status()
            cid = resp.json()["Hash"]
            self._local_cache[cid] = data
            logger.info("Pinned to local IPFS: %s (%d bytes)", cid, len(data))
            return cid

        except Exception as e:
            logger.warning("Local IPFS pin failed: %s, using local hash", e)
            return self._pin_local_hash(data)

    def _pin_local_hash(self, data: bytes) -> str:
        """
        Fallback: generate a deterministic CID-like hash.
        Data is stored in local memory cache for demo purposes.
        """
        # Generate CID-like hash (multihash format for development)
        content_hash = hashlib.sha256(data).hexdigest()
        cid = f"Qm{content_hash[:44]}"  # Development CIDv0 format
        self._local_cache[cid] = data
        logger.info("Local hash pin: %s (%d bytes)", cid, len(data))
        return cid

    def _fetch_gateway(self, cid: str) -> Optional[bytes]:
        """Fetch from IPFS public gateway."""
        import httpx

        gateways = [
            f"https://gateway.pinata.cloud/ipfs/{cid}",
            f"https://ipfs.io/ipfs/{cid}",
            f"https://dweb.link/ipfs/{cid}",
        ]

        for url in gateways:
            try:
                resp = httpx.get(url, timeout=10, follow_redirects=True)
                if resp.status_code == 200:
                    data = resp.content
                    self._local_cache[cid] = data
                    return data
            except Exception:
                continue

        return None

    def _fetch_local(self, cid: str) -> Optional[bytes]:
        """Fetch from local IPFS node."""
        import httpx

        try:
            resp = httpx.post(
                f"{self.ipfs_api_url}/api/v0/cat",
                params={"arg": cid},
                timeout=10,
            )
            if resp.status_code == 200:
                return resp.content
        except Exception:
            pass
        return None

    @classmethod
    def auto_detect(cls, **kwargs) -> "IPFSClient":
        """Create client with auto-detected backend."""
        return cls(backend="auto", **kwargs)

    def __repr__(self) -> str:
        cached = len(self._local_cache)
        return f"IPFSClient(backend={self.backend}, cached={cached})"
