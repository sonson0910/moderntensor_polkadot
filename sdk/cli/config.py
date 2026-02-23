"""
Configuration management for ModernTensor CLI
"""

import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field, asdict


@dataclass
class NetworkConfig:
    """Network configuration"""
    name: str = "testnet"
    rpc_url: str = "http://localhost:8545"
    chain_id: int = 8898  # Default to devnet
    explorer_url: Optional[str] = None


@dataclass
class WalletConfig:
    """Wallet configuration"""
    path: str = "~/.moderntensor/wallets"
    default_coldkey: Optional[str] = None
    default_hotkey: Optional[str] = None


@dataclass
class CLIConfig:
    """Main CLI configuration"""
    network: NetworkConfig = field(default_factory=NetworkConfig)
    wallet: WalletConfig = field(default_factory=WalletConfig)
    verbosity: int = 1
    use_cache: bool = True
    cache_ttl: int = 300  # seconds

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            'network': asdict(self.network),
            'wallet': asdict(self.wallet),
            'verbosity': self.verbosity,
            'use_cache': self.use_cache,
            'cache_ttl': self.cache_ttl,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CLIConfig':
        """Create config from dictionary"""
        config = cls()

        if 'network' in data:
            config.network = NetworkConfig(**data['network'])

        if 'wallet' in data:
            config.wallet = WalletConfig(**data['wallet'])

        config.verbosity = data.get('verbosity', 1)
        config.use_cache = data.get('use_cache', True)
        config.cache_ttl = data.get('cache_ttl', 300)

        return config

    @classmethod
    def load(cls, path: Optional[Path] = None) -> 'CLIConfig':
        """
        Load configuration from file

        Args:
            path: Path to config file. If None, uses default location.

        Returns:
            CLIConfig instance
        """
        if path is None:
            path = Path.home() / ".moderntensor" / "config.yaml"

        if not path.exists():
            return cls()

        try:
            with open(path, 'r') as f:
                data = yaml.safe_load(f)
                return cls.from_dict(data or {})
        except Exception:
            # Return default config if loading fails
            return cls()

    def save(self, path: Optional[Path] = None) -> None:
        """
        Save configuration to file

        Args:
            path: Path to config file. If None, uses default location.
        """
        if path is None:
            path = Path.home() / ".moderntensor" / "config.yaml"

        # Ensure directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False)


# Network presets for Polkadot Hub deployment
NETWORKS = {
    'polkadot_mainnet': NetworkConfig(
        name='polkadot_mainnet',
        rpc_url='https://asset-hub-eth-rpc.polkadot.io',
        chain_id=420420420,
        explorer_url='https://assethub-polkadot.subscan.io'
    ),
    # Official Polkadot Hub TestNet (Paseo-based)
    'polkadot_testnet': NetworkConfig(
        name='polkadot_testnet',
        rpc_url='https://services.polkadothub-rpc.com/testnet',
        chain_id=420420417,
        explorer_url='https://blockscout-westend.parity.io'
    ),
    # Legacy: Westend AssetHub
    'westend': NetworkConfig(
        name='westend',
        rpc_url='https://westend-asset-hub-eth-rpc.polkadot.io',
        chain_id=420420421,
        explorer_url='https://assethub-westend.subscan.io'
    ),
    'paseo_testnet': NetworkConfig(
        name='paseo_testnet',
        rpc_url='https://testnet-paseo-asset-hub-eth-rpc.polkadot.io',
        chain_id=420420422,
        explorer_url=None
    ),
    'local': NetworkConfig(
        name='local',
        rpc_url='http://localhost:8545',
        chain_id=1337,
        explorer_url=None
    ),
}


def get_network_config(network_name: str) -> NetworkConfig:
    """
    Get network configuration by name

    Args:
        network_name: Name of the network

    Returns:
        NetworkConfig instance

    Raises:
        ValueError: If network name is not recognized
    """
    if network_name not in NETWORKS:
        raise ValueError(
            f"Unknown network '{network_name}'. "
            f"Valid options: {', '.join(NETWORKS.keys())}"
        )

    return NETWORKS[network_name]
