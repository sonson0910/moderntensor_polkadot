# ModernTensor SDK

Python SDK for AI/ML model validation, scoring, and decentralized AI quality assurance on Polkadot Hub.

## Overview

The ModernTensor SDK provides tools for:

- **AI/ML Model Scoring** — Multi-dimensional quality scoring for AI model outputs
- **zkML Integration** — Zero-knowledge proof generation and verification for ML inference
- **Agent Framework** — Build AI agents that interact with on-chain smart contracts
- **Subnet Management** — Define and manage AI validation subnets
- **Tokenomics** — MDT token economics, emission, and staking calculations
- **Security** — Authentication, rate limiting, and API protection

## Quick Start

```python
# AI/ML scoring
from sdk.ai_ml.scoring import ModelScorer

scorer = ModelScorer()
score = scorer.evaluate(model_output, ground_truth)

# zkML proof generation
from sdk.ai_ml.zkml import ZkMLProver

prover = ZkMLProver()
proof = prover.generate_proof(model, input_data, output)

# Token utilities
from sdk import to_mdt, from_mdt, format_mdt

amount_wei = to_mdt(1.5)      # 1.5 MDT → wei
amount_mdt = from_mdt(amount_wei)  # wei → MDT
```

## Project Structure

```
sdk/
├── ai_ml/           # AI/ML framework
│   ├── agent/       # AI agent framework
│   ├── scoring/     # Model scoring & evaluation
│   ├── zkml/        # Zero-knowledge ML proofs
│   ├── subnets/     # Subnet definitions
│   ├── models/      # ML model registry
│   ├── processors/  # Data processors
│   └── core/        # Core AI utilities
├── security/        # Security module
├── tokenomics/      # Token economics
├── keymanager/      # Wallet & key management
├── cli/             # CLI tool (mtcli)
├── models/          # Data models
├── axon/            # API server framework
├── dendrite/        # Query client
├── synapse/         # Message protocol
├── config/          # Configuration
├── core/            # Core utilities (cache)
└── utils/           # Utilities
```

## Installation

```bash
pip install -e .
```

## CLI Usage

```bash
# Wallet management
mtcli wallet create-coldkey --name my_key
mtcli wallet list
mtcli utils convert --from-mdt 1.5
```
