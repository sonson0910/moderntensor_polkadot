"""Generate 3 wallets (deployer, validator, miner) from one mnemonic."""

from eth_account import Account

Account.enable_unaudited_hdwallet_features()

mnemonic = "false baby dumb latin attract stable lizard advance sport acquire pioneer couple"

# Deployer = index 0 (default)
deployer = Account.from_mnemonic(mnemonic)
print(f"Deployer:  {deployer.address}  key={deployer.key.hex()}")

# Validator = index 1
validator = Account.from_mnemonic(mnemonic, account_path="m/44'/60'/0'/0/1")
print(f"Validator: {validator.address}  key={validator.key.hex()}")

# Miner = index 2
miner = Account.from_mnemonic(mnemonic, account_path="m/44'/60'/0'/0/2")
print(f"Miner:     {miner.address}  key={miner.key.hex()}")
