# ModernTensor ✨

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**ModernTensor** is a decentralized AI quality protocol that enables AI/ML models to compete, validate, and earn rewards through on-chain smart contracts. **Deployed on Polkadot Hub** via `pallet-revive` EVM compatibility.

📄 **[Read the full Whitepaper (Vietnamese)](MODERNTENSOR_WHITEPAPER_VI.md)** | **[English Whitepaper](WHITEPAPER.md)**

![moderntensor.png](https://github.com/sonson0910/moderntensor/blob/main/moderntensor.png)

---

## 🔗 Polkadot Solidity Hackathon 2026

> **Track 1: EVM Smart Contract — AI-powered dApps** | Prize Pool: $15,000

ModernTensor deploys its complete AI protocol stack onto **Polkadot Hub (AssetHub)** via the `pallet-revive` EVM compatibility layer, bringing decentralized AI quality assurance to the Polkadot ecosystem.

### Deployed Smart Contracts

| Contract | Description | Lines |
|----------|-------------|-------|
| `MDTToken` | ERC20 token (21M supply, 8 allocation categories) | 188 |
| `MDTVesting` | Cliff + linear vesting schedules | ~150 |
| `MDTStaking` | Time-lock staking with 10-100% bonuses | 221 |
| `ZkMLVerifier` | On-chain zkML proof verification (STARK/Groth16) | 404 |
| `AIOracle` | AI request → fulfill oracle with payment | 335 |
| `GradientAggregator` | Federated learning (FedAvg on-chain) | ~380 |
| `TrainingEscrow` | Reward distribution + stake slashing | ~350 |
| `SubnetRegistry` | Yuma Consensus, metagraph, quadratic voting | 968 |
| `PaymentEscrow` | Pay-per-compute AI requests | ~200 |

Plus **13 more contracts** including AI examples (`AnomalyGuard`, `ContentAuthenticator`, `SemanticMatchmaker`, `TrustGraph`), templates (`LuxNFT`, `LuxToken`), interfaces, and libraries.

### Architecture on Polkadot Hub

```
┌─────────────────────────────────────────────────┐
│              Polkadot Hub (AssetHub)             │
│            pallet-revive (EVM Layer)             │
├─────────────────────────────────────────────────┤
│                                                 │
│  MDTToken ──→ MDTStaking (Lock + Bonus)         │
│     │                                           │
│     ├──→ MDTVesting (Team/Investor vesting)     │
│     │                                           │
│     ├──→ AIOracle ──→ ZkMLVerifier              │
│     │    (AI requests)  (Proof verification)    │
│     │                                           │
│     ├──→ GradientAggregator (FedAvg)            │
│     │    (Training jobs + rounds)               │
│     │                                           │
│     ├──→ TrainingEscrow (Rewards + Slashing)    │
│     │    PaymentEscrow (Pay-per-compute)        │
│     │                                           │
│     └──→ SubnetRegistry (Yuma Consensus)        │
│          (Metagraph + Quadratic Voting)         │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start — Deploy to Polkadot Hub

### Prerequisites

- Node.js 18+
- MetaMask browser extension
- [Polkadot testnet tokens](https://faucet.polkadot.io/) (WND for Westend AssetHub)

### Deploy

```bash
# 1. Install dependencies
cd luxtensor/contracts
npm install

# 2. Configure your wallet
cp .env.example .env
# Edit .env: set PRIVATE_KEY=<your-metamask-private-key>

# 3. Add Polkadot Hub to MetaMask
# Network Name: Westend AssetHub
# RPC URL: https://westend-asset-hub-eth-rpc.polkadot.io
# Chain ID: 420420421
# Currency: WND

# 4. Get testnet tokens
# Visit: https://faucet.polkadot.io/ → select Westend AssetHub

# 5. Deploy all 8 contracts
npx hardhat run scripts/deploy-polkadot.js --network polkadot_testnet

# 6. View deployed addresses
cat deployments-polkadot.json
```

### Available Networks

| Network | Chain ID | RPC Endpoint |
|---------|----------|-------------|
| Westend AssetHub (testnet) | `420420421` | `https://westend-asset-hub-eth-rpc.polkadot.io` |
| Paseo AssetHub (testnet) | `420420422` | `https://testnet-paseo-asset-hub-eth-rpc.polkadot.io` |
| Polkadot Hub (mainnet) | `420420420` | `https://asset-hub-eth-rpc.polkadot.io` |

---

## 📋 Features

### Smart Contracts (Solidity 0.8.20)

- **MDT Token** — ERC20 with category-based minting (Emission 45%, Ecosystem 12%, Team 10%, etc.), burnable, permit
- **Staking** — Time-lock staking with tiered bonus rates: 30d→10%, 90d→25%, 180d→50%, 365d→100%
- **AI Oracle** — Decentralized AI request/fulfill pattern with model registry, timeout mechanism, protocol fees
- **zkML Verification** — On-chain zero-knowledge ML proof verification (RISC Zero STARK, Groth16, dev mode)
- **Federated Learning** — On-chain gradient aggregation (FedAvg), multi-round training jobs, Proof of Training
- **Training Escrow** — Stake-gated training participation, reward distribution, slashing for invalid proofs
- **Vesting** — Cliff + linear vesting schedules for team, investors, ecosystem allocations

### Python SDK

- **LuxtensorClient** — Comprehensive RPC client (sync + async)
- **AI/ML Framework** — Agent system, scoring, subnet management, zkML integration
- **Consensus Module** — PoS, slashing, fork choice, fast finality
- **CLI (`mtcli`)** — Wallet management, staking, queries, transactions
- **Security** — Authentication, rate limiting, IP filtering, DDoS protection

### Tokenomics

| Category | Allocation | Amount |
|----------|-----------|--------|
| Emission Rewards | 45% | 9,450,000 MDT |
| Ecosystem Grants | 12% | 2,520,000 MDT |
| Team & Core Dev | 10% | 2,100,000 MDT |
| Private Sale | 8% | 1,680,000 MDT |
| IDO | 5% | 1,050,000 MDT |
| DAO Treasury | 10% | 2,100,000 MDT |
| Initial Liquidity | 5% | 1,050,000 MDT |
| Foundation Reserve | 5% | 1,050,000 MDT |
| **Total** | **100%** | **21,000,000 MDT** |

---

## 🏗️ Project Structure

```
moderntensor/
├── luxtensor/
│   └── contracts/           # Solidity smart contracts
│       ├── src/             # Contract source files (21 contracts)
│       ├── scripts/         # Deploy scripts (Hardhat)
│       ├── artifacts/       # Compiled contract ABIs
│       ├── hardhat.config.js
│       └── package.json
├── sdk/                     # Python SDK (162 files)
│   ├── ai_ml/              # AI/ML framework
│   ├── consensus/           # PoS consensus
│   ├── cli/                # CLI tool (mtcli)
│   ├── client/             # RPC client mixins
│   ├── security/           # Security module
│   └── tokenomics/         # Token economics
├── tests/                   # Test suite (27 test files)
├── docs/                    # Documentation
├── docker/                  # Docker configurations
└── README.md
```

---

## ⚙️ Installation

### Smart Contracts

```bash
cd luxtensor/contracts
npm install
npx hardhat compile
npx hardhat test
```

### Python SDK

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### CLI Quick Start

```bash
# Check version
mtcli --version

# Create a wallet
mtcli wallet create-coldkey --name my_coldkey

# Generate hotkey
mtcli wallet generate-hotkey --coldkey my_coldkey --hotkey-name miner_hk1

# List wallets
mtcli wallet list
```

---

## 📚 Documentation

* **[ModernTensor Whitepaper (Vietnamese)](MODERNTENSOR_WHITEPAPER_VI.md)** — Complete project whitepaper
* **[Whitepaper (English)](WHITEPAPER.md)** — English version
* **[Tokenomics](docs/TOKENOMICS.md)** — Token distribution and economics
* **[Pitch Deck](docs/PITCH_DECK.md)** — Project overview presentation
* **[Changelog](CHANGELOG.md)** — Version history

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
