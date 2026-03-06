from web3 import Web3

w3 = Web3(Web3.HTTPProvider("https://westend-asset-hub-eth-rpc.polkadot.io"))
deployer = "0x350EB21005e911f4493a93449DDD329dE1fd7964"
validator = "0x7453dc226c58C5758eDd9De79162Fe2aeFDf229D"
miner = "0x54C375b935344fC3c16E5e83F444DB54dE0E6eB9"

print(f"Chain ID: {w3.eth.chain_id}")
print(f"Block: {w3.eth.block_number}")
print(f"Deployer  balance: {Web3.from_wei(w3.eth.get_balance(deployer), 'ether')} WND")
print(f"Validator balance: {Web3.from_wei(w3.eth.get_balance(validator), 'ether')} WND")
print(f"Miner     balance: {Web3.from_wei(w3.eth.get_balance(miner), 'ether')} WND")
