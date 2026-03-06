"""Transfer WND from Miner to Deployer and Validator on Westend Asset Hub."""

from web3 import Web3

RPC = "https://westend-asset-hub-eth-rpc.polkadot.io"
w3 = Web3(Web3.HTTPProvider(RPC))

MINER_KEY = "2191a9482334c6dcd94d58e5a0d929037c77b990d8a259fbb009a9812305da72"
MINER_ADDR = "0x54C375b935344fC3c16E5e83F444DB54dE0E6eB9"
DEPLOYER_ADDR = "0x350EB21005e911f4493a93449DDD329dE1fd7964"
VALIDATOR_ADDR = "0x7453dc226c58C5758eDd9De79162Fe2aeFDf229D"

chain_id = w3.eth.chain_id
print(f"Chain ID: {chain_id}")
print(f"Miner balance: {Web3.from_wei(w3.eth.get_balance(MINER_ADDR), 'ether')} WND")

# Transfer 6 WND to Deployer
nonce = w3.eth.get_transaction_count(MINER_ADDR)
gas_price = w3.eth.gas_price

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
print(f"\n✅ Miner → Deployer: 6 WND")
print(f"   TX: {receipt1.transactionHash.hex()}")
print(f"   Status: {'Success' if receipt1.status == 1 else 'Failed'}")

# Transfer 2 WND to Validator
nonce2 = w3.eth.get_transaction_count(MINER_ADDR)
tx2 = {
    "to": VALIDATOR_ADDR,
    "value": Web3.to_wei(2, "ether"),
    "gas": 21000,
    "gasPrice": gas_price,
    "nonce": nonce2,
    "chainId": chain_id,
}
signed2 = w3.eth.account.sign_transaction(tx2, MINER_KEY)
tx_hash2 = w3.eth.send_raw_transaction(signed2.raw_transaction)
receipt2 = w3.eth.wait_for_transaction_receipt(tx_hash2, timeout=120)
print(f"\n✅ Miner → Validator: 2 WND")
print(f"   TX: {receipt2.transactionHash.hex()}")
print(f"   Status: {'Success' if receipt2.status == 1 else 'Failed'}")

# Final balances
print(f"\n=== Final Balances ===")
print(f"Deployer:  {Web3.from_wei(w3.eth.get_balance(DEPLOYER_ADDR), 'ether')} WND")
print(f"Validator: {Web3.from_wei(w3.eth.get_balance(VALIDATOR_ADDR), 'ether')} WND")
print(f"Miner:     {Web3.from_wei(w3.eth.get_balance(MINER_ADDR), 'ether')} WND")
