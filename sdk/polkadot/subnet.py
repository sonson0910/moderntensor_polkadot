"""
SubnetClient — SubnetRegistry wrapper.

Enhanced Yuma Consensus with Security Hardening:
1. Subnet creation & management
2. Node registration (with self-vote protection)
3. Commit-reveal weight setting (anti front-running)
4. Epoch-based emission distribution (quadratic voting + trust)
5. Slashing (penalty for malicious validators)
6. Stake delegation
7. Metagraph queries with trust scores
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING, Optional

logger = logging.getLogger(__name__)

from web3 import Web3

if TYPE_CHECKING:
    from .client import PolkadotClient


class NodeType(IntEnum):
    """Node type in subnet."""

    MINER = 0
    VALIDATOR = 1


@dataclass
class SubnetInfo:
    """On-chain subnet metadata."""

    netuid: int
    name: str
    owner: str
    max_nodes: int
    emission_share: int  # basis points
    tempo: int  # blocks per epoch
    node_count: int
    active: bool

    @property
    def emission_percent(self) -> float:
        return self.emission_share / 100.0


@dataclass
class NodeInfo:
    """On-chain node (neuron) info — includes trust score."""

    uid: int
    hotkey: str
    coldkey: str
    node_type: NodeType
    stake: int  # wei
    delegated_stake: int  # wei
    rank: int  # scaled 1e18
    incentive: int  # accumulated
    emission: int  # pending to claim
    trust: int  # trust score (0 - 1e18)
    active: bool

    @property
    def total_stake_ether(self) -> float:
        return float(Web3.from_wei(self.stake + self.delegated_stake, "ether"))

    @property
    def emission_ether(self) -> float:
        return float(Web3.from_wei(self.emission, "ether"))

    @property
    def rank_float(self) -> float:
        return self.rank / 1e18 if self.rank > 0 else 0.0

    @property
    def trust_float(self) -> float:
        """Trust score as float 0.0 - 1.0."""
        return self.trust / 1e18 if self.trust > 0 else 0.0

    @property
    def is_miner(self) -> bool:
        return self.node_type == NodeType.MINER

    @property
    def is_validator(self) -> bool:
        return self.node_type == NodeType.VALIDATOR


@dataclass
class Metagraph:
    """Full metagraph snapshot for a subnet."""

    netuid: int
    nodes: list[NodeInfo]

    @property
    def miners(self) -> list[NodeInfo]:
        return [n for n in self.nodes if n.is_miner and n.active]

    @property
    def validators(self) -> list[NodeInfo]:
        return [n for n in self.nodes if n.is_validator and n.active]

    @property
    def total_stake(self) -> int:
        return sum(n.stake + n.delegated_stake for n in self.nodes if n.active)

    def get_node(self, uid: int) -> Optional[NodeInfo]:
        for n in self.nodes:
            if n.uid == uid:
                return n
        return None


class SubnetClient:
    """SubnetRegistry operations — on-chain metagraph + secure consensus."""

    def __init__(self, client: PolkadotClient) -> None:
        self._client = client
        self._contract = client._get_contract("SubnetRegistry")

    # ═══════════════════════════════════════════════════════
    # Subnet Management
    # ═══════════════════════════════════════════════════════

    def create_subnet(
        self,
        name: str,
        max_nodes: int = 256,
        min_stake_ether: float = 0,
        tempo: int = 360,
    ) -> tuple[str, int]:
        """
        Create a new subnet. Burns registration cost.

        Args:
            name: Human-readable subnet name (max 64 chars)
            max_nodes: Maximum neurons allowed
            min_stake_ether: Minimum MDT stake to register a node
            tempo: Blocks per epoch for emission

        Returns:
            Tuple of (tx_hash, netuid) — the assigned subnet ID
        """
        # The contract's nextNetuid is the ID that will be assigned
        next_id = self._contract.functions.nextNetuid().call()
        min_stake_wei = Web3.to_wei(min_stake_ether, "ether")
        tx = self._contract.functions.createSubnet(
            name, max_nodes, min_stake_wei, tempo
        ).build_transaction({})
        tx_hash = self._client.send_tx(tx)
        return tx_hash, next_id

    def update_subnet(
        self,
        netuid: int,
        max_nodes: int,
        min_stake_ether: float,
        tempo: int,
        immunity_period: int = 7200,
    ) -> str:
        """Update subnet parameters (subnet owner only)."""
        min_stake_wei = Web3.to_wei(min_stake_ether, "ether")
        tx = self._contract.functions.updateSubnet(
            netuid, max_nodes, min_stake_wei, tempo, immunity_period
        ).build_transaction({})
        return self._client.send_tx(tx)

    def update_emission_share(self, netuid: int, new_share_bps: int) -> str:
        """
        Update subnet emission share (subnet owner or admin only).

        Args:
            netuid: Target subnet
            new_share_bps: New emission share in basis points (1-10000, e.g. 1000 = 10%)

        Returns:
            Transaction hash
        """
        tx = self._contract.functions.updateEmissionShare(netuid, new_share_bps).build_transaction(
            {}
        )
        return self._client.send_tx(tx)

    def get_subnet(self, netuid: int) -> SubnetInfo:
        """Get subnet info."""
        result = self._contract.functions.getSubnet(netuid).call()
        return SubnetInfo(
            netuid=netuid,
            name=result[0],
            owner=result[1],
            max_nodes=result[2],
            emission_share=result[3],
            tempo=result[4],
            node_count=result[5],
            active=result[6],
        )

    def get_subnet_count(self) -> int:
        """Get total number of created subnets (excluding root)."""
        # Contract returns nextNetuid, actual count = nextNetuid - 1
        # (netuid 0 is reserved for root, first real subnet = 1)
        return self._contract.functions.getSubnetCount().call() - 1

    def next_netuid(self) -> int:
        """Get the next netuid that will be assigned."""
        return self._contract.functions.nextNetuid().call()

    # ═══════════════════════════════════════════════════════
    # Node Registration (with Self-Vote Protection)
    # ═══════════════════════════════════════════════════════

    def register_miner(
        self,
        netuid: int,
        hotkey: Optional[str] = None,
        stake_ether: float = 0,
    ) -> str:
        """
        Register as a miner in a subnet.

        SECURITY: Will revert if the same coldkey (msg.sender) is already
        registered as a VALIDATOR in this subnet (self-vote protection).

        Args:
            netuid: Target subnet
            hotkey: Network identity (defaults to caller address)
            stake_ether: Initial stake in MDT

        Returns:
            Transaction hash
        """
        hk = Web3.to_checksum_address(hotkey or self._client.address)
        stake_wei = Web3.to_wei(stake_ether, "ether")
        tx = self._contract.functions.registerNode(
            netuid, hk, NodeType.MINER, stake_wei
        ).build_transaction({})
        return self._client.send_tx(tx)

    def register_validator(
        self,
        netuid: int,
        hotkey: Optional[str] = None,
        stake_ether: float = 0,
    ) -> str:
        """
        Register as a validator in a subnet.

        SECURITY: Will revert if the same coldkey (msg.sender) is already
        registered as a MINER in this subnet (self-vote protection).

        Args:
            netuid: Target subnet
            hotkey: Network identity (defaults to caller address)
            stake_ether: Initial stake in MDT

        Returns:
            Transaction hash
        """
        hk = Web3.to_checksum_address(hotkey or self._client.address)
        stake_wei = Web3.to_wei(stake_ether, "ether")
        tx = self._contract.functions.registerNode(
            netuid, hk, NodeType.VALIDATOR, stake_wei
        ).build_transaction({})
        return self._client.send_tx(tx)

    def deregister(self, netuid: int, uid: int) -> str:
        """Deregister a node and return stake."""
        tx = self._contract.functions.deregisterNode(netuid, uid).build_transaction({})
        return self._client.send_tx(tx)

    def is_registered(self, netuid: int, hotkey: Optional[str] = None) -> bool:
        """Check if hotkey is registered in subnet."""
        hk = Web3.to_checksum_address(hotkey or self._client.address)
        return self._contract.functions.isRegistered(netuid, hk).call()

    def get_uid(self, netuid: int, hotkey: Optional[str] = None) -> int:
        """Get UID for a registered hotkey."""
        hk = Web3.to_checksum_address(hotkey or self._client.address)
        return self._contract.functions.getUidByHotkey(netuid, hk).call()

    # ═══════════════════════════════════════════════════════
    # Commit-Reveal Weight Setting (Anti Front-Running)
    # ═══════════════════════════════════════════════════════

    def commit_weights(
        self,
        netuid: int,
        uids: list[int],
        weights: list[int],
        salt: Optional[bytes] = None,
    ) -> tuple[str, bytes]:
        """
        Phase 1: Commit weight hash (anti front-running).

        Validators must commit a hash of their weights first,
        then reveal them in a separate transaction after a delay.
        This prevents other validators from seeing and copying weights.

        Args:
            netuid: Target subnet
            uids: List of miner UIDs to score
            weights: List of weights (uint16, 0-65535)
            salt: Random salt (auto-generated if not provided)

        Returns:
            Tuple of (tx_hash, salt) — keep the salt for reveal!
        """
        if salt is None:
            salt = secrets.token_bytes(32)

        # Compute hash matching Solidity: keccak256(abi.encodePacked(uids, weights, salt))
        # abi.encodePacked for uint16[] pads each element to 32 bytes
        commit_hash = Web3.solidity_keccak(
            ["uint16[]", "uint16[]", "bytes32"],
            [uids, weights, salt],
        )

        tx = self._contract.functions.commitWeights(netuid, commit_hash).build_transaction({})
        tx_hash = self._client.send_tx(tx)

        return tx_hash, salt

    def reveal_weights(
        self,
        netuid: int,
        uids: list[int],
        weights: list[int],
        salt: bytes,
    ) -> str:
        """
        Phase 2: Reveal weights (must match committed hash).

        Must be called after commitMinDelay blocks and before
        commitRevealWindow blocks from the commit.

        Args:
            netuid: Target subnet
            uids: List of miner UIDs (same as commit)
            weights: List of weights (same as commit)
            salt: Salt used in commit_weights

        Returns:
            Transaction hash
        """
        tx = self._contract.functions.revealWeights(netuid, uids, weights, salt).build_transaction(
            {}
        )
        return self._client.send_tx(tx)

    def set_weights(
        self,
        netuid: int,
        uids: list[int],
        weights: list[int],
        validator_uid: int = None,
    ) -> str:
        """
        Legacy setWeights (admin override, without commit-reveal).

        Owner can set weights directly (emergency/migration).
        Prefer commit_weights + reveal_weights for production use.

        Args:
            netuid: Target subnet
            uids: List of miner UIDs to score
            weights: List of weights (uint16, 0-65535)
            validator_uid: (ignored, kept for backward-compat)

        Returns:
            Transaction hash

        Example:
            >>> client.subnet.set_weights(1, [0, 1, 2], [100, 200, 50])
        """
        # Contract signature: setWeights(uint256 netuid, uint16 validatorUid, uint16[] uids, uint16[] weights)
        vid = validator_uid if validator_uid is not None else 0
        tx = self._contract.functions.setWeights(netuid, vid, uids, weights).build_transaction({})
        return self._client.send_tx(tx)

    def get_weights(self, netuid: int, validator_uid: int) -> tuple[list[int], list[int]]:
        """Get weights set by a validator."""
        result = self._contract.functions.getWeights(netuid, validator_uid).call()
        return list(result[0]), list(result[1])

    # ═══════════════════════════════════════════════════════
    # Emission Distribution (Enhanced Yuma Consensus)
    # ═══════════════════════════════════════════════════════

    def run_epoch(self, netuid: int) -> str:
        """
        Trigger epoch — distribute emission with Enhanced Yuma Consensus.

        Security features applied:
        1. QUADRATIC voting: sqrt(stake) instead of raw stake
        2. TRUST multiplier: high-trust validators count more (up to 1.5x)
        3. PROPORTIONAL validator share: based on stake, not equal
        4. TRUST UPDATES: auto-computed from consensus alignment

        Can be called by anyone when enough blocks pass.

        Returns:
            Transaction hash
        """
        tx = self._contract.functions.runEpoch(netuid).build_transaction({})
        return self._client.send_tx(tx)

    def claim_emission(self, netuid: int, uid: int) -> str:
        """Claim accumulated emission rewards."""
        tx = self._contract.functions.claimEmission(netuid, uid).build_transaction({})
        return self._client.send_tx(tx)

    # ═══════════════════════════════════════════════════════
    # Slashing
    # ═══════════════════════════════════════════════════════

    def slash_node(
        self,
        netuid: int,
        uid: int,
        basis_points: int = 500,
        reason: str = "Malicious behavior",
    ) -> str:
        """
        Slash a node's stake. Slashed tokens recycled as emission.

        Only callable by contract owner or subnet owner.

        Args:
            netuid: Target subnet
            uid: Node UID to slash
            basis_points: Slash percentage (500 = 5%, max 10000 = 100%)
            reason: Human-readable reason for slashing

        Returns:
            Transaction hash
        """
        tx = self._contract.functions.slashNode(
            netuid, uid, basis_points, reason
        ).build_transaction({})
        return self._client.send_tx(tx)

    def auto_slash_inactive(self, netuid: int, validator_uid: int) -> str:
        """
        Auto-slash an inactive validator (1% penalty).

        Anyone can call this if the validator hasn't set weights
        for more than maxWeightAge blocks (~24h).

        Args:
            netuid: Target subnet
            validator_uid: Validator UID to slash

        Returns:
            Transaction hash
        """
        tx = self._contract.functions.autoSlashInactive(netuid, validator_uid).build_transaction({})
        return self._client.send_tx(tx)

    # ═══════════════════════════════════════════════════════
    # Delegation
    # ═══════════════════════════════════════════════════════

    def delegate(self, netuid: int, validator_uid: int, amount_ether: float) -> str:
        """
        Delegate stake to a validator.

        Args:
            netuid: Target subnet
            validator_uid: Validator UID to delegate to
            amount_ether: MDT amount to delegate

        Returns:
            Transaction hash
        """
        amount_wei = Web3.to_wei(amount_ether, "ether")
        tx = self._contract.functions.delegate(netuid, validator_uid, amount_wei).build_transaction(
            {}
        )
        return self._client.send_tx(tx)

    def undelegate(self, netuid: int, validator_uid: int, amount_ether: float) -> str:
        """Undelegate stake from a validator."""
        amount_wei = Web3.to_wei(amount_ether, "ether")
        tx = self._contract.functions.undelegate(
            netuid, validator_uid, amount_wei
        ).build_transaction({})
        return self._client.send_tx(tx)

    def get_delegation(
        self,
        netuid: int,
        validator_uid: int,
        delegator: Optional[str] = None,
    ) -> int:
        """Get delegation amount (wei)."""
        addr = Web3.to_checksum_address(delegator or self._client.address)
        return self._contract.functions.getDelegation(addr, netuid, validator_uid).call()

    # ═══════════════════════════════════════════════════════
    # Emission Pool
    # ═══════════════════════════════════════════════════════

    def fund_emission_pool(self, amount_ether: float) -> str:
        """
        Fund the emission pool with MDT tokens.

        Requires prior approve() of MDT tokens to SubnetRegistry.
        The emission pool is used by runEpoch() to distribute rewards.

        Args:
            amount_ether: Amount of MDT to fund (human-readable)

        Returns:
            Transaction hash
        """
        amount_wei = Web3.to_wei(amount_ether, "ether")
        tx = self._contract.functions.fundEmissionPool(amount_wei).build_transaction({})
        return self._client.send_tx(tx)

    # ═══════════════════════════════════════════════════════
    # Trust Score Queries
    # ═══════════════════════════════════════════════════════

    def get_trust(self, netuid: int, uid: int) -> float:
        """
        Get trust score of a node (0.0 - 1.0).

        Trust is computed by runEpoch() based on how well
        the validator's weights align with consensus.

        Returns:
            Trust score as float (0.0 to 1.0)
        """
        raw = self._contract.functions.getTrust(netuid, uid).call()
        return raw / 1e18 if raw > 0 else 0.0

    def get_validator_score(self, netuid: int, uid: int) -> dict:
        """
        Get full validator consensus score breakdown.

        Returns all metrics that determine a validator's emission share:
        - trust: Consensus alignment score (0.0-1.0)
        - rank: Rank from last epoch (0.0-1.0)
        - stake: Direct stake in ether
        - delegated_stake: Delegated stake in ether
        - effective_power: sqrt(totalStake) × trustMultiplier
        - emission: Pending emission in ether
        - incentive: Accumulated incentive in ether
        - active: Whether node is active

        Args:
            netuid: Target subnet
            uid: Validator UID

        Returns:
            Dict with all validator consensus metrics

        Example:
            >>> score = client.subnet.get_validator_score(1, 0)
            >>> print(f"Trust: {score['trust']:.2%}")
            >>> print(f"Power: {score['effective_power']}")
        """
        result = self._contract.functions.getValidatorScore(netuid, uid).call()
        return {
            "trust": result[0] / 1e18 if result[0] > 0 else 0.0,
            "rank": result[1] / 1e18 if result[1] > 0 else 0.0,
            "stake": float(Web3.from_wei(result[2], "ether")),
            "delegated_stake": float(Web3.from_wei(result[3], "ether")),
            "effective_power": result[4],
            "emission": float(Web3.from_wei(result[5], "ether")),
            "incentive": float(Web3.from_wei(result[6], "ether")),
            "active": result[7],
        }

    # ═══════════════════════════════════════════════════════
    # Metagraph
    # ═══════════════════════════════════════════════════════

    def get_metagraph(self, netuid: int) -> Metagraph:
        """
        Get full metagraph snapshot for a subnet.

        Returns:
            Metagraph with all nodes, stakes, ranks, emissions.
        """
        result = self._contract.functions.getMetagraph(netuid).call()
        hotkeys, coldkeys, stakes, ranks, incentives, emissions, types, actives = result

        nodes = []
        for i in range(len(hotkeys)):
            # Fetch per-node data for accurate stake/delegatedStake split
            try:
                node_info = self.get_node(netuid, i)
                nodes.append(node_info)
            except Exception:
                # Fallback: use metagraph data with total stake as own stake
                nodes.append(
                    NodeInfo(
                        uid=i,
                        hotkey=hotkeys[i],
                        coldkey=coldkeys[i],
                        node_type=NodeType(types[i]),
                        stake=stakes[i],
                        delegated_stake=0,
                        rank=ranks[i],
                        incentive=incentives[i],
                        emission=emissions[i],
                        trust=0,
                        active=actives[i],
                    )
                )

        return Metagraph(netuid=netuid, nodes=nodes)

    def get_node(self, netuid: int, uid: int) -> NodeInfo:
        """Get single node info (includes trust score)."""
        result = self._contract.functions.getNode(netuid, uid).call()
        return NodeInfo(
            uid=uid,
            hotkey=result[0],
            coldkey=result[1],
            node_type=NodeType(result[2]),
            stake=result[3],
            delegated_stake=result[4],
            rank=result[5],
            incentive=result[6],
            emission=result[7],
            trust=result[8],
            active=result[9],
        )

    # ═══════════════════════════════════════════════════════
    # Convenience
    # ═══════════════════════════════════════════════════════

    def approve_and_register_miner(
        self, netuid: int, stake_ether: float, hotkey: Optional[str] = None
    ) -> tuple[str, str]:
        """Approve MDT + register as miner."""
        stake_wei = Web3.to_wei(stake_ether, "ether")
        approve_hash = self._client.token.approve(self._contract.address, stake_wei)
        reg_hash = self.register_miner(netuid, hotkey, stake_ether)
        return approve_hash, reg_hash

    def approve_and_register_validator(
        self, netuid: int, stake_ether: float, hotkey: Optional[str] = None
    ) -> tuple[str, str]:
        """Approve MDT + register as validator."""
        stake_wei = Web3.to_wei(stake_ether, "ether")
        approve_hash = self._client.token.approve(self._contract.address, stake_wei)
        reg_hash = self.register_validator(netuid, hotkey, stake_ether)
        return approve_hash, reg_hash

    def approve_and_delegate(
        self, netuid: int, validator_uid: int, amount_ether: float
    ) -> tuple[str, str]:
        """Approve MDT + delegate to validator."""
        amount_wei = Web3.to_wei(amount_ether, "ether")
        approve_hash = self._client.token.approve(self._contract.address, amount_wei)
        delegate_hash = self.delegate(netuid, validator_uid, amount_ether)
        return approve_hash, delegate_hash

    # ═══════════════════════════════════════════════════════
    # Admin Config
    # ═══════════════════════════════════════════════════════

    def set_zkml_verifier(self, verifier_address: str) -> str:
        """Set ZkML verifier address on contract (owner only)."""
        tx = self._contract.functions.setZkmlVerifier(
            Web3.to_checksum_address(verifier_address)
        ).build_transaction({})
        return self._client.send_tx(tx)

    def set_slash_percentage(self, basis_points: int) -> str:
        """Set default slash percentage (owner only, max 50%)."""
        tx = self._contract.functions.setSlashPercentage(basis_points).build_transaction({})
        return self._client.send_tx(tx)

    def set_commit_reveal_window(self, blocks: int) -> str:
        """Set commit-reveal window in blocks (owner only)."""
        tx = self._contract.functions.setCommitRevealWindow(blocks).build_transaction({})
        return self._client.send_tx(tx)

    def get_emission_config(self) -> dict:
        """Get global emission and security configuration from contract.

        Returns:
            Dict with emission_per_block, total_emission_shares, slash_percentage,
            commit_reveal_window, commit_min_delay, max_weight_age.
        """
        c = self._contract.functions
        return {
            "emission_per_block": c.emissionPerBlock().call(),
            "total_emission_shares": c.totalEmissionShares().call(),
            "slash_percentage": c.slashPercentage().call(),
            "commit_reveal_window": c.commitRevealWindow().call(),
            "commit_min_delay": c.commitMinDelay().call(),
            "max_weight_age": c.maxWeightAge().call(),
            "subnet_registration_cost": c.subnetRegistrationCost().call(),
        }

    def __repr__(self) -> str:
        try:
            count = self.get_subnet_count()
            return f"SubnetClient(subnets={count})"
        except Exception:
            return "SubnetClient(not connected)"
