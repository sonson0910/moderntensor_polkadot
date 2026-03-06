"""Transfer WND on Westend Asset Hub — with proper gas estimation."""

from web3 import Web3

RPC = "https://westend-asset-hub-eth-rpc.polkadot.io"
w3 = Web3(Web3.HTTPProvider(RPC))

MINER_KEY = "2191a9482334c6dcd94d58e5a0d929037c77b990d8a259fbb009a9812305da72"
MINER_ADDR = "0x54C375b935344fC3c16E5e83F444DB54dE0E6eB9"
DEPLOYER_ADDR = "0x350EB21005e911f4493a93449DDD329dE1fd7964"
VALIDATOR_ADDR = "0x7453dc226c58C5758eDd9De79162Fe2aeFDf229D"

chain_id = w3.eth.chain_id
print(f"Chain ID: {chain_id}")
print(f"Gas price: {w3.eth.gas_price}")

miner_bal = w3.eth.get_balance(MINER_ADDR)
print(f"Miner balance: {Web3.from_wei(miner_bal, 'ether')} WND ({miner_bal} wei)")

nonce = w3.eth.get_transaction_count(MINER_ADDR)
print(f"Miner nonce: {nonce}")

# Try estimating gas for a simple transfer
try:
    est = w3.eth.estimate_gas(
        {
            "from": MINER_ADDR,
            "to": DEPLOYER_ADDR,
            "value": Web3.to_wei(1, "ether"),
        }
    )
    print(f"Estimated gas: {est}")
except Exception as e:
    print(f"Gas estimation error: {e}")

# Try with EIP-1559 (type 2 tx)
try:
    base_fee = w3.eth.get_block("latest").get("baseFeePerGas", 0)
    print(f"Base fee: {base_fee}")
except Exception as e:
    print(f"No base fee: {e}")

# Attempt transfer with type 2 tx
print("\n--- Attempting transfer ---")
try:
    tx1 = {
        "from": MINER_ADDR,
        "to": DEPLOYER_ADDR,
        "value": Web3.to_wei(6, "ether"),
        "nonce": nonce,
        "chainId": chain_id,
        "type": 2,
        "maxFeePerGas": w3.eth.gas_price * 2,
        "maxPriorityFeePerGas": w3.eth.gas_price,
        "gas": 21000,
    }
    signed1 = w3.eth.account.sign_transaction(tx1, MINER_KEY)
    tx_hash1 = w3.eth.send_raw_transaction(signed1.raw_transaction)
    receipt1 = w3.eth.wait_for_transaction_receipt(tx_hash1, timeout=120)
    print(f"✅ Miner → Deployer: 6 WND | TX: {receipt1.transactionHash.hex()}")
except Exception as e:
    print(f"Type 2 failed: {e}")
    # Try legacy tx with explicit gas price
    try:
        gas_price = max(w3.eth.gas_price, 1_000_000_000)  # min 1 Gwei
        tx1 = {
            "to": DEPLOYER_ADDR,
            "value": Web3.to_wei(6, "ether"),
            "gas": 21000,
            "gasPrice": gas_price,
            "nonce": nonce,
            "chainId": chain_id,
        }
        signed1 = w3.eth.account.sign_transaction(tx1, MINER_KEY)
        tx_hash1 = w3.eth.send_raw_transaction(signed1.raw_transaction)
        receipt1 = w3.eth.wait_for_transaction_receipt(tx_hash1, timeout=120)
        print(f"✅ Miner → Deployer: 6 WND (legacy) | TX: {receipt1.transactionHash.hex()}")
    except Exception as e2:
        print(f"Legacy also failed: {e2}")
