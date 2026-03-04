"""
EventListener — Contract event subscriptions.

Enables miners/validators to listen for on-chain events:
- AI requests (for miners to fulfill)
- Staking events (for governance/monitoring)
- Subnet registration and weight events
"""

from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING, Any, Callable, Optional

from web3 import Web3

if TYPE_CHECKING:
    from .client import PolkadotClient

logger = logging.getLogger(__name__)


class EventListener:
    """
    Poll-based event listener for ModernTensor contracts.

    Usage:
        # One-shot: get recent events
        events = client.events.get_ai_requests(from_block="latest")

        # Continuous: poll for new events
        client.events.poll_events("AIOracle", "AIRequestCreated", callback)
    """

    def __init__(self, client: PolkadotClient) -> None:
        self._client = client

    # ── AI Oracle Events ────────────────────────────────────

    def get_ai_requests(
        self,
        from_block: int | str = "latest",
        to_block: int | str = "latest",
    ) -> list[dict[str, Any]]:
        """Get AIRequestCreated events."""
        contract = self._client._get_contract("AIOracle")
        event_filter = contract.events.AIRequestCreated.create_filter(
            fromBlock=from_block, toBlock=to_block
        )
        return [dict(e["args"]) for e in event_filter.get_all_entries()]

    def get_fulfilled_requests(
        self,
        from_block: int | str = "latest",
        to_block: int | str = "latest",
    ) -> list[dict[str, Any]]:
        """Get AIRequestFulfilled events."""
        contract = self._client._get_contract("AIOracle")
        event_filter = contract.events.AIRequestFulfilled.create_filter(
            fromBlock=from_block, toBlock=to_block
        )
        return [dict(e["args"]) for e in event_filter.get_all_entries()]

    # ── Staking Events ──────────────────────────────────────

    def get_staking_events(
        self,
        from_block: int | str = "latest",
        to_block: int | str = "latest",
    ) -> list[dict[str, Any]]:
        """Get Staked events from MDTStaking."""
        contract = self._client._get_contract("MDTStaking")
        event_filter = contract.events.Staked.create_filter(fromBlock=from_block, toBlock=to_block)
        return [dict(e["args"]) for e in event_filter.get_all_entries()]

    # ── SubnetRegistry v2 Events ────────────────────────────

    def get_subnet_created(
        self,
        from_block: int | str = "latest",
        to_block: int | str = "latest",
    ) -> list[dict[str, Any]]:
        """Get SubnetCreated events."""
        return self.get_events("SubnetRegistry", "SubnetCreated", from_block, to_block)

    def get_node_registered(
        self,
        from_block: int | str = "latest",
        to_block: int | str = "latest",
    ) -> list[dict[str, Any]]:
        """Get NodeRegistered events."""
        return self.get_events("SubnetRegistry", "NodeRegistered", from_block, to_block)

    def get_weights_committed(
        self,
        from_block: int | str = "latest",
        to_block: int | str = "latest",
    ) -> list[dict[str, Any]]:
        """Get WeightsCommitted events."""
        return self.get_events("SubnetRegistry", "WeightsCommitted", from_block, to_block)

    def get_slash_events(
        self,
        from_block: int | str = "latest",
        to_block: int | str = "latest",
    ) -> list[dict[str, Any]]:
        """Get NodeSlashed events."""
        return self.get_events("SubnetRegistry", "NodeSlashed", from_block, to_block)

    def get_epoch_events(
        self,
        from_block: int | str = "latest",
        to_block: int | str = "latest",
    ) -> list[dict[str, Any]]:
        """Get EpochCompleted events."""
        return self.get_events("SubnetRegistry", "EpochCompleted", from_block, to_block)

    # ── Generic Polling ─────────────────────────────────────

    def poll_events(
        self,
        contract_name: str,
        event_name: str,
        callback: Callable[[dict[str, Any]], None],
        poll_interval: float = 2.0,
        from_block: int | str = "latest",
        stop_event: Optional[threading.Event] = None,
    ) -> None:
        """
        Continuously poll for new events.

        Args:
            contract_name: Contract name (e.g. 'AIOracle')
            event_name: Event name (e.g. 'AIRequestCreated')
            callback: Function called for each new event
            poll_interval: Seconds between polls
            from_block: Starting block
            stop_event: Optional threading.Event to signal graceful shutdown

        Note:
            This is a blocking call. Run in a thread for async.
            Set stop_event to allow graceful shutdown.

        Example:
            >>> stop = threading.Event()
            >>> def on_request(event):
            ...     print(f"New AI request: {event}")
            >>> client.events.poll_events("AIOracle", "AIRequestCreated", on_request, stop_event=stop)
        """
        contract = self._client._get_contract(contract_name)
        event_obj = getattr(contract.events, event_name)

        last_block = from_block if isinstance(from_block, int) else self._client.block_number

        logger.info(
            "Polling %s.%s from block %d (interval=%.1fs)",
            contract_name,
            event_name,
            last_block,
            poll_interval,
        )

        while not (stop_event and stop_event.is_set()):
            try:
                current_block = self._client.block_number
                if current_block > last_block:
                    event_filter = event_obj.create_filter(
                        fromBlock=last_block + 1,
                        toBlock=current_block,
                    )
                    for entry in event_filter.get_all_entries():
                        callback(dict(entry["args"]))
                    last_block = current_block
            except Exception as e:
                logger.warning("Poll error: %s", e)

            time.sleep(poll_interval)

    def listen(
        self,
        contract_name: str,
        event_name: str,
        callback: Callable[[dict[str, Any]], None],
        poll_interval: float = 2.0,
    ) -> None:
        """
        Convenience alias for poll_events.

        Example:
            >>> client.events.listen("SubnetRegistry", "NodeRegistered", handler)
        """
        self.poll_events(contract_name, event_name, callback, poll_interval)

    def get_events(
        self,
        contract_name: str,
        event_name: str,
        from_block: int | str = "latest",
        to_block: int | str = "latest",
    ) -> list[dict[str, Any]]:
        """
        Generic event getter for any contract event.

        Example:
            >>> events = client.events.get_events("SubnetRegistry", "NodeRegistered")
        """
        contract = self._client._get_contract(contract_name)
        event_obj = getattr(contract.events, event_name)
        event_filter = event_obj.create_filter(fromBlock=from_block, toBlock=to_block)
        return [dict(e["args"]) for e in event_filter.get_all_entries()]

    def __repr__(self) -> str:
        return "EventListener(poll-based)"
