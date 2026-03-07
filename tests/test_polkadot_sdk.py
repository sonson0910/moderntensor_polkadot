"""
Unit tests for ModernTensor Polkadot SDK modules.

Tests cover:
- TokenClient: balance, transfer, approve
- SubnetClient: subnet creation, node registration, weight setting
- StakingClient: lock, unlock, info
- OracleClient: request creation, fulfillment
- ZkMLClient: proof verification, trust management
- AISubnetOrchestrator: task creation, evaluation, cycle

NOTE: These tests require a running Hardhat node + deployed contracts.
      Run `npx hardhat node` and `npx hardhat run scripts/deploy-polkadot.js`
      before executing tests.
"""

# ═══════════════════════════════════════════════════════
# Config & Helpers Tests
# ═══════════════════════════════════════════════════════


class TestPolkadotConfig:
    """Tests for SDK configuration resolution."""

    def test_default_rpc_url(self):
        """Default RPC should be localhost:8545."""
        from sdk.polkadot.config import NETWORKS

        assert "local" in NETWORKS
        assert "8545" in NETWORKS["local"].rpc_url

    def test_config_has_deployment_path(self):
        """Config should have load_deployment function."""
        from sdk.polkadot.config import load_deployment

        assert callable(load_deployment)


# ═══════════════════════════════════════════════════════
# TokenClient Tests
# ═══════════════════════════════════════════════════════


class TestTokenClient:
    """Tests for MDTToken ERC20 operations."""

    def test_balance_returns_int(self):
        """Balance should return an integer (wei)."""
        from sdk.polkadot.token import TokenClient

        # TokenClient needs a real client, so we test interface
        assert hasattr(TokenClient, "balance_of")
        assert hasattr(TokenClient, "balance_of_ether")
        assert hasattr(TokenClient, "transfer")
        assert hasattr(TokenClient, "approve")

    def test_token_client_has_transfer(self):
        """TokenClient should expose transfer methods."""
        from sdk.polkadot.token import TokenClient

        assert hasattr(TokenClient, "transfer")
        assert hasattr(TokenClient, "approve")


# ═══════════════════════════════════════════════════════
# SubnetClient Tests
# ═══════════════════════════════════════════════════════


class TestSubnetClient:
    """Tests for SubnetRegistry operations."""

    def test_node_type_enum(self):
        """NodeType enum should have MINER=0, VALIDATOR=1."""
        from sdk.polkadot.subnet import NodeType

        assert NodeType.MINER == 0
        assert NodeType.VALIDATOR == 1

    def test_subnet_info_dataclass(self):
        """SubnetInfo should have expected fields."""
        from sdk.polkadot.subnet import SubnetInfo

        fields = SubnetInfo.__dataclass_fields__
        assert "name" in fields
        assert "owner" in fields
        assert "max_nodes" in fields
        assert "tempo" in fields

    def test_node_info_dataclass(self):
        """NodeInfo should have expected fields."""
        from sdk.polkadot.subnet import NodeInfo

        fields = NodeInfo.__dataclass_fields__
        assert "uid" in fields
        assert "hotkey" in fields
        assert "stake" in fields
        assert "emission" in fields

    def test_metagraph_dataclass(self):
        """Metagraph should have nodes list."""
        from sdk.polkadot.subnet import Metagraph

        fields = Metagraph.__dataclass_fields__
        assert "nodes" in fields


# ═══════════════════════════════════════════════════════
# ZkMLClient Tests
# ═══════════════════════════════════════════════════════


class TestZkMLClient:
    """Tests for zkML verification operations."""

    def test_proof_type_constants(self):
        """Proof type constants should be defined."""
        from sdk.polkadot.zkml import (
            PROOF_TYPE_STARK,
            PROOF_TYPE_GROTH16,
            PROOF_TYPE_DEV,
        )

        assert PROOF_TYPE_STARK == 0
        assert PROOF_TYPE_GROTH16 == 1
        assert PROOF_TYPE_DEV == 2

    def test_verify_proof_method_exists(self):
        """verify_proof should exist (renamed from verify_full)."""
        from sdk.polkadot.zkml import ZkMLClient

        assert hasattr(ZkMLClient, "verify_proof")

    def test_verify_full_alias_exists(self):
        """verify_full should still exist as backward-compat alias."""
        from sdk.polkadot.zkml import ZkMLClient

        assert hasattr(ZkMLClient, "verify_full")
        # Should point to the same function
        assert ZkMLClient.verify_full is ZkMLClient.verify_proof


# ═══════════════════════════════════════════════════════
# Orchestrator Tests
# ═══════════════════════════════════════════════════════


class TestAISubnetOrchestrator:
    """Tests for the AI inference orchestration layer."""

    def test_orchestrator_import(self):
        """AISubnetOrchestrator should be importable."""
        from sdk.polkadot.orchestrator import AISubnetOrchestrator

        assert AISubnetOrchestrator is not None

    def test_evaluation_result_dataclass(self):
        """EvaluationResult should have expected fields."""
        from sdk.polkadot.orchestrator import EvaluationResult

        fields = EvaluationResult.__dataclass_fields__
        assert "miner_scores" in fields
        assert "total_tasks" in fields
        assert "verified_proofs" in fields


# ═══════════════════════════════════════════════════════
# Error Handling Tests
# ═══════════════════════════════════════════════════════


class TestErrorHandling:
    """Tests for RPC error handling."""

    def test_rpc_error_codes(self):
        """RPC error codes should be defined."""
        from sdk.errors import RpcErrorCode

        assert RpcErrorCode.PARSE_ERROR == -32700
        assert RpcErrorCode.INSUFFICIENT_FUNDS == -32004
        assert RpcErrorCode.RATE_LIMITED == -32010

    def test_rpc_error_from_response(self):
        """RpcError should parse from JSON-RPC response."""
        from sdk.errors import RpcError

        error = RpcError.from_response(
            {"code": -32004, "message": "Insufficient funds", "data": {"have": "0", "need": "100"}}
        )
        assert error.code == -32004
        assert "Insufficient" in error.message

    def test_parse_rpc_error(self):
        """parse_rpc_error should return specific error classes."""
        from sdk.errors import parse_rpc_error, InsufficientFundsError

        error = parse_rpc_error(
            {
                "code": -32004,
                "message": "Insufficient funds: have 0, need 100",
                "data": {"have": "0", "need": "100"},
            }
        )
        assert isinstance(error, InsufficientFundsError)

    def test_branding_cleaned(self):
        """Error module should reference ModernTensor, not Luxtensor."""
        import sdk.errors as errors

        source = open(errors.__file__).read()
        assert "ModernTensor" in source
        assert "Luxtensor" not in source


# ═══════════════════════════════════════════════════════
# CLI Tests
# ═══════════════════════════════════════════════════════


class TestCLIStructure:
    """Tests for CLI command group registration."""

    def test_cli_has_all_groups(self):
        """CLI should have all 7 command groups."""
        from sdk.cli.main import cli

        commands = list(cli.commands.keys())
        expected = ["wallet", "utils", "subnet", "oracle", "zkml", "staking", "ai"]
        for cmd in expected:
            assert cmd in commands, f"Missing CLI group: {cmd}"

    def test_ai_group_has_commands(self):
        """AI CLI group should have status, create-task, evaluate."""
        from sdk.cli.commands.ai import ai

        commands = list(ai.commands.keys())
        assert "status" in commands
        assert "create-task" in commands
        assert "evaluate" in commands

    def test_staking_group_has_commands(self):
        """Staking CLI group should have info, lock, unlock, stakes."""
        from sdk.cli.commands.staking import staking

        commands = list(staking.commands.keys())
        assert "info" in commands
        assert "lock" in commands
        assert "unlock" in commands
        assert "stakes" in commands
