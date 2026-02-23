# ModernTensor SDK — Quick Start

## Installation

```bash
# Clone and install
cd moderntensor
pip install -e .
```

## AI/ML Scoring

```python
from sdk.ai_ml.scoring import ModelScorer

# Score an AI model's output quality
scorer = ModelScorer()
result = scorer.evaluate(
    model_output="Generated response text...",
    expected_output="Expected response text...",
    metrics=["accuracy", "coherence", "helpfulness"]
)
print(f"Quality Score: {result.overall_score}")
```

## zkML Proofs

Generate zero-knowledge proofs for ML inference:

```python
from sdk.ai_ml.zkml import ZkMLProver

prover = ZkMLProver()
proof = prover.generate_proof(
    model_hash="0x...",
    input_data=input_tensor,
    output_data=output_tensor
)
# Submit proof to ZkMLVerifier contract on Polkadot Hub
```

## Token Utilities

```python
from sdk import to_mdt, from_mdt, format_mdt, validate_address

# Unit conversion
wei_amount = to_mdt(1.5)           # 1.5 MDT → smallest unit
mdt_amount = from_mdt(wei_amount)  # → 1.5 MDT
formatted = format_mdt(wei_amount) # → "1.500000 MDT"

# Address validation
is_valid = validate_address("0x...")
```

## Smart Contract Integration

Deploy and interact with ModernTensor contracts on Polkadot Hub:

```bash
cd luxtensor/contracts
npm install
npx hardhat run scripts/deploy-polkadot.js --network polkadot_testnet
```

See [deploy-polkadot.js](../luxtensor/contracts/scripts/deploy-polkadot.js) for full deployment.
