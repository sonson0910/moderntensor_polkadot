"""
PolkadotClient — Main entry point for ModernTensor on Polkadot Hub.

Provides unified access to all on-chain contract functionality:
- Token management (MDT ERC20 + Vesting)
- Staking with time-lock bonuses
- AI Oracle requests & fulfillment
- zkML proof verification
- Subnet Registry (metagraph, consensus, emission)
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from web3.exceptions import TransactionNotFound, TimeExhausted
from eth_account import Account
from eth_account.signers.local import LocalAccount

from sdk.contracts import get_abi
from .config import NETWORKS, NetworkConfig, load_deployment
from .token import TokenClient
from .staking import StakingClient
from .oracle import OracleClient
from .zkml import ZkMLClient
from .events import EventListener
from .subnet import SubnetClient
from .training import TrainingClient
from .escrow import EscrowClient
from .orchestrator import AISubnetOrchestrator

logger = logging.getLogger(__name__)

# Safety cap to prevent runaway gas costs
MAX_GAS_LIMIT = 5_000_000


class PolkadotClient:
    """
    Unified client for ModernTensor contracts on Polkadot Hub.

    Usage:
        client = PolkadotClient(
            network="polkadot_testnet",
            private_key="0x...",
            deployment_path="deployments-polkadot.json",
        )

        # Check MDT balance
        balance = client.token.balance_of(client.address)

        # Stake tokens
        client.staking.lock(amount_ether=100, lock_days=90)

        # Create AI request
        request_id = client.oracle.request_ai(model_hash, input_data)
    """

    def __init__(
        self,
        network: str = "polkadot_testnet",
        rpc_url: Optional[str] = None,
        private_key: Optional[str] = None,
        deployment_path: Optional[str] = None,
        contracts: Optional[dict[str, str]] = None,
    ) -> None:
        """
        Initialize PolkadotClient.

        Args:
            network: Network name from NETWORKS (e.g. 'polkadot_testnet')
            rpc_url: Override RPC URL (takes precedence over network config)
            private_key: Private key for signing transactions
            deployment_path: Path to deployments-polkadot.json
            contracts: Direct contract address mapping (overrides deployment_path)
        """
        # Network config
        if network in NETWORKS:
            self._network = NETWORKS[network]
        else:
            self._network = NetworkConfig(name=network, rpc_url=rpc_url or "", chain_id=0)

        url = rpc_url or self._network.rpc_url
        if not url:
            raise ValueError(f"No RPC URL for network '{network}'")

        # Web3 connection
        self.w3 = Web3(Web3.HTTPProvider(url))
        # PoA middleware for Polkadot Hub
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        # Account setup
        self._account: Optional[LocalAccount] = None
        if private_key:
            self._account = Account.from_key(private_key)
            self.w3.eth.default_account = self._account.address
            logger.info("Account loaded: %s", self._account.address)

        # Load contract addresses
        if contracts:
            self._addresses = contracts
        else:
            try:
                self._addresses = load_deployment(deployment_path, network)
            except FileNotFoundError:
                logger.warning("No deployment file found. Use contracts= param.")
                self._addresses = {}

        # Initialize sub-clients
        self._token: Optional[TokenClient] = None
        self._staking: Optional[StakingClient] = None
        self._oracle: Optional[OracleClient] = None
        self._zkml: Optional[ZkMLClient] = None
        self._events: Optional[EventListener] = None
        self._subnet: Optional[SubnetClient] = None
        self._training: Optional[TrainingClient] = None
        self._escrow: Optional[EscrowClient] = None

        # Nonce management lock to prevent race conditions
        self._nonce_lock = threading.Lock()

    # ── Properties ──────────────────────────────────────────

    @property
    def address(self) -> str:
        """Current account address."""
        if self._account is None:
            raise ValueError("No private key configured")
        return self._account.address

    @property
    def is_connected(self) -> bool:
        """Check if web3 is connected to RPC."""
        return self.w3.is_connected()

    @property
    def chain_id(self) -> int:
        """Current chain ID."""
        return self.w3.eth.chain_id

    @property
    def block_number(self) -> int:
        """Latest block number."""
        return self.w3.eth.block_number

    # ── Sub-Clients (lazy init) ─────────────────────────────

    @property
    def token(self) -> TokenClient:
        """MDTToken + MDTVesting client."""
        if self._token is None:
            self._token = TokenClient(self)
        return self._token

    @property
    def staking(self) -> StakingClient:
        """MDTStaking client."""
        if self._staking is None:
            self._staking = StakingClient(self)
        return self._staking

    @property
    def oracle(self) -> OracleClient:
        """AIOracle client."""
        if self._oracle is None:
            self._oracle = OracleClient(self)
        return self._oracle

    @property
    def zkml(self) -> ZkMLClient:
        """ZkMLVerifier client."""
        if self._zkml is None:
            self._zkml = ZkMLClient(self)
        return self._zkml

    @property
    def events(self) -> EventListener:
        """Event listener for contract events."""
        if self._events is None:
            self._events = EventListener(self)
        return self._events

    @property
    def subnet(self) -> SubnetClient:
        """SubnetRegistry client — metagraph, key reg, weights, emission."""
        if self._subnet is None:
            self._subnet = SubnetClient(self)
        return self._subnet

    @property
    def training(self) -> TrainingClient:
        """GradientAggregator client — federated learning (FedAvg)."""
        if self._training is None:
            self._training = TrainingClient(self)
        return self._training

    @property
    def escrow(self) -> EscrowClient:
        """TrainingEscrow client — stake-gated training with slashing."""
        if self._escrow is None:
            self._escrow = EscrowClient(self)
        return self._escrow

    def orchestrator(self, netuid: int = 1) -> AISubnetOrchestrator:
        """Create an AI Subnet Orchestrator for the given subnet.

        The orchestrator ties Oracle + ZkML + Subnet into one
        coherent workflow: tasks → inference → proofs → weights.
        """
        return AISubnetOrchestrator(self, netuid=netuid)

    # ── Transaction Helpers ─────────────────────────────────

    def _get_contract(self, name: str) -> Any:
        """Get a web3 contract instance by name."""
        address = self._addresses.get(name)
        if not address:
            raise ValueError(
                f"No address for contract '{name}'. " f"Available: {list(self._addresses.keys())}"
            )
        abi = get_abi(name)
        return self.w3.eth.contract(
            address=Web3.to_checksum_address(address),
            abi=abi,
        )

    def send_tx(
        self,
        tx: dict[str, Any],
        timeout: int = 300,
        retries: int = 3,
    ) -> str:
        """
        Sign and send a transaction, wait for receipt.

        Retries with exponential backoff for transient RPC failures.

        Args:
            tx: Transaction dict (to, data, value, etc.)
            timeout: Seconds to wait for confirmation (default 300s for testnets)
            retries: Max retry attempts for transient failures

        Returns:
            Transaction hash as hex string.
        """
        if self._account is None:
            raise ValueError("No private key configured for signing")

        last_err: Exception | None = None

        for attempt in range(retries):
            try:
                with self._nonce_lock:
                    # Build transaction (re-fetch nonce each attempt)
                    tx_copy = dict(tx)
                    tx_copy.setdefault("from", self._account.address)
                    tx_copy.setdefault("chainId", self.chain_id)
                    tx_copy["nonce"] = self.w3.eth.get_transaction_count(
                        self._account.address, "pending"
                    )

                    if "gas" not in tx_copy:
                        estimated_gas = self.w3.eth.estimate_gas(tx_copy)
                        tx_copy["gas"] = min(estimated_gas, MAX_GAS_LIMIT)
                    else:
                        tx_copy["gas"] = min(tx_copy["gas"], MAX_GAS_LIMIT)

                # Use EIP-1559 fields for compatibility with modern nodes
                if "maxFeePerGas" not in tx_copy and "gasPrice" not in tx_copy:
                    try:
                        base_fee = self.w3.eth.get_block("latest").get("baseFeePerGas", 0)
                        priority_fee = self.w3.eth.max_priority_fee
                        tx_copy["maxPriorityFeePerGas"] = priority_fee
                        tx_copy["maxFeePerGas"] = base_fee * 2 + priority_fee
                    except Exception:
                        tx_copy["gasPrice"] = self.w3.eth.gas_price

                # Sign and send
                signed = self._account.sign_transaction(tx_copy)
                tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)

                # Wait for confirmation
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
                if receipt["status"] != 1:
                    # Try to extract revert reason for better debugging
                    reason = f"TX reverted: {tx_hash.hex()}"
                    try:
                        self.w3.eth.call(
                            {k: v for k, v in tx_copy.items() if k != "gas"},
                            receipt["blockNumber"],
                        )
                    except Exception as revert_err:
                        reason = f"TX reverted ({revert_err}): {tx_hash.hex()}"
                    raise RuntimeError(reason)

                logger.info("TX confirmed: %s (gas: %d)", tx_hash.hex(), receipt["gasUsed"])
                return tx_hash.hex()

            except RuntimeError:
                raise  # Don't retry on-chain reverts
            except (ConnectionError, TimeoutError, TransactionNotFound, TimeExhausted) as e:
                last_err = e
                if attempt < retries - 1:
                    wait = 2**attempt
                    logger.warning(
                        "TX attempt %d/%d failed, retrying in %ds: %s",
                        attempt + 1,
                        retries,
                        wait,
                        e,
                    )
                    time.sleep(wait)

        raise RuntimeError(f"TX failed after {retries} attempts: {last_err}") from last_err

    def get_eth_balance(self, address: Optional[str] = None) -> int:
        """Get native token balance (wei)."""
        addr = address or self.address
        return self.w3.eth.get_balance(Web3.to_checksum_address(addr))

    def __repr__(self) -> str:
        status = "connected" if self.is_connected else "disconnected"
        addr = self._account.address[:10] + "..." if self._account else "no-account"
        return f"PolkadotClient(network={self._network.name}, {status}, {addr})"
