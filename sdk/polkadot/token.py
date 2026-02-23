"""
TokenClient — MDTToken + MDTVesting wrapper.

Provides:
- ERC20: balance_of, transfer, approve, allowance
- TGE: execute_tge, get_allocation
- Vesting: create_team_vesting, create_private_sale_vesting,
           create_ido_vesting, claim_vested, claimable
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from web3 import Web3

if TYPE_CHECKING:
    from .client import PolkadotClient


@dataclass
class VestingScheduleInfo:
    """Individual vesting schedule details."""
    total_amount: int       # wei
    claimed_amount: int     # wei
    start_time: int         # unix timestamp
    cliff_duration: int     # seconds
    vesting_duration: int   # seconds
    tge_percent: int        # 0-100
    revocable: bool
    revoked: bool

    @property
    def total_amount_ether(self) -> float:
        return float(Web3.from_wei(self.total_amount, "ether"))

    @property
    def claimed_amount_ether(self) -> float:
        return float(Web3.from_wei(self.claimed_amount, "ether"))


class TokenClient:
    """MDTToken + MDTVesting operations."""

    def __init__(self, client: PolkadotClient) -> None:
        self._client = client
        self._token = client._get_contract("MDTToken")
        try:
            self._vesting = client._get_contract("MDTVesting")
        except ValueError:
            self._vesting = None

    # ── ERC20 Read ──────────────────────────────────────────

    def balance_of(self, address: Optional[str] = None) -> int:
        """Get MDT token balance (wei)."""
        addr = address or self._client.address
        return self._token.functions.balanceOf(
            Web3.to_checksum_address(addr)
        ).call()

    def balance_of_ether(self, address: Optional[str] = None) -> float:
        """Get MDT token balance in ether units."""
        return Web3.from_wei(self.balance_of(address), "ether")

    def total_supply(self) -> int:
        """Total MDT supply (wei)."""
        return self._token.functions.totalSupply().call()

    def allowance(self, owner: str, spender: str) -> int:
        """Check allowance."""
        return self._token.functions.allowance(
            Web3.to_checksum_address(owner),
            Web3.to_checksum_address(spender),
        ).call()

    def name(self) -> str:
        """Token name."""
        return self._token.functions.name().call()

    def symbol(self) -> str:
        """Token symbol."""
        return self._token.functions.symbol().call()

    def decimals(self) -> int:
        """Token decimals."""
        return self._token.functions.decimals().call()

    # ── ERC20 Write ─────────────────────────────────────────

    def transfer(self, to: str, amount: int) -> str:
        """
        Transfer MDT tokens.

        Args:
            to: Recipient address
            amount: Amount in wei

        Returns:
            Transaction hash
        """
        tx = self._token.functions.transfer(
            Web3.to_checksum_address(to),
            amount,
        ).build_transaction({})
        return self._client.send_tx(tx)

    def approve(self, spender: str, amount: int) -> str:
        """
        Approve spender to use tokens.

        Args:
            spender: Contract/address to approve
            amount: Amount in wei

        Returns:
            Transaction hash
        """
        tx = self._token.functions.approve(
            Web3.to_checksum_address(spender),
            amount,
        ).build_transaction({})
        return self._client.send_tx(tx)

    def transfer_ether(self, to: str, amount_ether: float) -> str:
        """Transfer MDT in ether units (human-readable)."""
        amount_wei = Web3.to_wei(amount_ether, "ether")
        return self.transfer(to, amount_wei)

    # ── TGE & Minting ────────────────────────────────────────

    # Category enum matching MDTToken.sol
    CAT_EMISSION_REWARDS = 0
    CAT_ECOSYSTEM_GRANTS = 1
    CAT_TEAM_CORE_DEV = 2
    CAT_PRIVATE_SALE = 3
    CAT_IDO = 4
    CAT_DAO_TREASURY = 5
    CAT_INITIAL_LIQUIDITY = 6
    CAT_FOUNDATION_RESERVE = 7

    def execute_tge(self, category: int = 0, to: str | None = None) -> str:
        """
        Execute Token Generation Event for a category (owner only).

        Args:
            category: Category enum (0-7, see CAT_* constants)
            to: Recipient address (defaults to caller)

        Returns:
            Transaction hash
        """
        recipient = Web3.to_checksum_address(to or self._client.address)
        tx = self._token.functions.executeTGE(
            category, recipient
        ).build_transaction({})
        return self._client.send_tx(tx)

    def mint_category(self, category: int, to: str, amount: int) -> str:
        """Mint specific amount from a category (owner only)."""
        tx = self._token.functions.mintCategory(
            category,
            Web3.to_checksum_address(to),
            amount,
        ).build_transaction({})
        return self._client.send_tx(tx)

    def tge_executed(self) -> bool:
        """Check if TGE has been executed."""
        return self._token.functions.tgeTimestamp().call() > 0

    def remaining_allocation(self, category: int) -> int:
        """Get remaining allocation for a category (wei)."""
        return self._token.functions.remainingAllocation(category).call()

    # ── Vesting ─────────────────────────────────────────────
    # Maps to MDTVesting.sol: createTeamVesting, createPrivateSaleVesting,
    # createIDOVesting, claim, claimable, vestedAmount, getVestingInfo

    def _require_vesting(self) -> None:
        """Ensure MDTVesting contract is available."""
        if self._vesting is None:
            raise ValueError("MDTVesting contract not deployed")

    def set_tge_timestamp(self, timestamp: int = 0) -> str:
        """
        Set TGE timestamp (owner only). Pass 0 to use current block time.

        Args:
            timestamp: Unix timestamp for TGE start (0 = block.timestamp)

        Returns:
            Transaction hash
        """
        self._require_vesting()
        tx = self._vesting.functions.setTGETimestamp(
            timestamp
        ).build_transaction({})
        return self._client.send_tx(tx)

    def create_team_vesting(self, beneficiary: str, amount: int) -> str:
        """
        Create Team/Core Dev vesting (1yr cliff + 4yr linear, 0% TGE, revocable).

        Args:
            beneficiary: Recipient address
            amount: Token amount in wei

        Returns:
            Transaction hash
        """
        self._require_vesting()
        tx = self._vesting.functions.createTeamVesting(
            Web3.to_checksum_address(beneficiary),
            amount,
        ).build_transaction({})
        return self._client.send_tx(tx)

    def create_private_sale_vesting(self, beneficiary: str, amount: int) -> str:
        """
        Create Private Sale vesting (1yr cliff + 2yr linear, 0% TGE, non-revocable).

        Args:
            beneficiary: Recipient address
            amount: Token amount in wei

        Returns:
            Transaction hash
        """
        self._require_vesting()
        tx = self._vesting.functions.createPrivateSaleVesting(
            Web3.to_checksum_address(beneficiary),
            amount,
        ).build_transaction({})
        return self._client.send_tx(tx)

    def create_ido_vesting(self, beneficiary: str, amount: int) -> str:
        """
        Create IDO vesting (25% TGE + 6mo linear, non-revocable).

        Args:
            beneficiary: Recipient address
            amount: Token amount in wei

        Returns:
            Transaction hash
        """
        self._require_vesting()
        tx = self._vesting.functions.createIDOVesting(
            Web3.to_checksum_address(beneficiary),
            amount,
        ).build_transaction({})
        return self._client.send_tx(tx)

    def claim_vested(self) -> str:
        """
        Claim all vested tokens for caller across all schedules.

        Returns:
            Transaction hash
        """
        self._require_vesting()
        tx = self._vesting.functions.claim().build_transaction({})
        return self._client.send_tx(tx)

    def claimable(self, address: Optional[str] = None) -> int:
        """
        Get total claimable (vested but unclaimed) amount in wei.

        Args:
            address: Beneficiary address (defaults to caller)

        Returns:
            Claimable amount in wei
        """
        self._require_vesting()
        addr = address or self._client.address
        return self._vesting.functions.claimable(
            Web3.to_checksum_address(addr)
        ).call()

    def claimable_ether(self, address: Optional[str] = None) -> float:
        """Get claimable amount in ether units."""
        return float(Web3.from_wei(self.claimable(address), "ether"))

    def vested_amount(self, address: str, index: int) -> int:
        """
        Get vested amount for a specific schedule (wei).

        Args:
            address: Beneficiary address
            index: Schedule index

        Returns:
            Vested amount in wei
        """
        self._require_vesting()
        return self._vesting.functions.vestedAmount(
            Web3.to_checksum_address(address), index
        ).call()

    def get_vesting_info(self, address: Optional[str] = None) -> list[VestingScheduleInfo]:
        """
        Get all vesting schedules for a beneficiary.

        Args:
            address: Beneficiary address (defaults to caller)

        Returns:
            List of VestingScheduleInfo
        """
        self._require_vesting()
        addr = address or self._client.address
        result = self._vesting.functions.getVestingInfo(
            Web3.to_checksum_address(addr)
        ).call()
        schedules = []
        for s in result:
            schedules.append(VestingScheduleInfo(
                total_amount=s[0],
                claimed_amount=s[1],
                start_time=s[2],
                cliff_duration=s[3],
                vesting_duration=s[4],
                tge_percent=s[5],
                revocable=s[6],
                revoked=s[7],
            ))
        return schedules

    def __repr__(self) -> str:
        try:
            sym = self.symbol()
            supply = self.balance_of_ether()
            return f"TokenClient({sym}, balance={supply:.2f})"
        except Exception:
            return "TokenClient(not connected)"
