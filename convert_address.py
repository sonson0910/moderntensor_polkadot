"""Convert EVM 0x addresses to Westend SS58 format for faucet."""

import hashlib


def evm_to_substrate_ss58(evm_address: str, ss58_prefix: int = 42) -> str:
    """
    Convert EVM address to Substrate SS58 using the 'evm:' prefix mapping.
    Westend uses SS58 prefix 42.
    """
    # Remove 0x prefix and convert to bytes
    evm_bytes = bytes.fromhex(evm_address[2:].lower())

    # Create the AccountId32 from EVM address:
    # Substrate maps EVM addresses using: blake2b256(b"evm:" + evm_address_bytes)
    # Actually for AssetHub EVM, the mapping is direct padding:
    # AccountId32 = 0x000000000000000000000000 + evm_address (20 bytes padded to 32)

    # Method: pad EVM address to 32 bytes (left-pad with zeros)
    account_id = b"\x00" * 12 + evm_bytes  # 12 + 20 = 32 bytes

    # SS58 encoding
    # Payload: prefix_byte + account_id
    if ss58_prefix < 64:
        prefix_bytes = bytes([ss58_prefix])
    else:
        # Two-byte prefix
        first = ((ss58_prefix & 0b11111100) >> 2) | 0b01000000
        second = (ss58_prefix >> 8) | ((ss58_prefix & 0b11) << 6)
        prefix_bytes = bytes([first, second])

    payload = prefix_bytes + account_id

    # SS58 checksum
    checksum_prefix = b"SS58PRE"
    checksum = hashlib.blake2b(checksum_prefix + payload, digest_size=64).digest()[:2]

    # Base58 encode
    import base58

    return base58.b58encode(payload + checksum).decode()


deployer = "0x350EB21005e911f4493a93449DDD329dE1fd7964"
validator = "0x7453dc226c58C5758eDd9De79162Fe2aeFDf229D"
miner = "0x54C375b935344fC3c16E5e83F444DB54dE0E6eB9"

print("=== EVM → Westend SS58 Address Mapping ===")
print()
print(f"Deployer  EVM: {deployer}")
print(f"Deployer  SS58: {evm_to_substrate_ss58(deployer)}")
print()
print(f"Validator EVM: {validator}")
print(f"Validator SS58: {evm_to_substrate_ss58(validator)}")
print()
print(f"Miner     EVM: {miner}")
print(f"Miner     SS58: {evm_to_substrate_ss58(miner)}")
print()
print("=== Faucet Instructions ===")
print("1. Go to: https://faucet.polkadot.io/westend?parachain=1000")
print("2. Or Matrix: https://matrix.to/#/#westend_faucet:matrix.org")
print("   Type: !drip <SS58_address>")
print()
print("NOTE: You need WND on Asset Hub (parachain 1000), not relay chain!")
