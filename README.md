# ModernTensor ✨

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**ModernTensor** is a decentralized AI quality protocol that enables AI/ML models to compete, validate, and earn rewards through on-chain smart contracts. **Deployed on Polkadot Hub** via `pallet-revive` EVM compatibility.

📄 **[Read the full Whitepaper (Vietnamese)](MODERNTENSOR_WHITEPAPER_VI.md)** | **[English Whitepaper](WHITEPAPER.md)**

![moderntensor.png](./moderntensor.png)

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

Plus **11 more contracts** including AI examples (`AnomalyGuard`, `ContentAuthenticator`, `SemanticMatchmaker`, `TrustGraph`), templates (`LuxNFT`, `LuxToken`, `PaymentEscrow`), interfaces, and libraries.

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
npx hardhat run scripts/deploy-polkadot.js --network polkadotTestnet

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

### 🖥️ Web Frontend (Cyberpunk Dashboard)

- **Subnets Hub** — BIOS boot animation, live network stats (Total Subnets, Active Nodes, Emissions)
- **Subnet Detail + Metagraph** — Interactive node table with UID, Stake, Trust, Incentive, 24h performance; filter Miners/Validators
- **Validators** — Trust scores, staking amounts, validation activity
- **Tokenomics + Yield Simulator** — Token distribution chart, interactive APY calculator with sliders
- **Tech:** Next.js 15 + React 19 + Tailwind CSS, glassmorphism UI, real-time on-chain data

### Smart Contracts (Solidity 0.8.28)

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
- **Polkadot Integration** — On-chain subnet management, staking, IPFS storage, oracle, training orchestration
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
moderntensor_polkadot/
├── web/                     # 🖥️ Web Frontend (Next.js 15 + React 19)
│   ├── app/                 # App Router pages
│   │   ├── page.tsx         # Subnets Hub (landing)
│   │   ├── subnet/[id]/     # Subnet Detail + Metagraph
│   │   ├── validators/      # Validators page
│   │   └── tokenomics/      # Tokenomics + Yield Simulator
│   ├── components/          # React components
│   └── package.json
├── luxtensor/
│   └── contracts/           # Solidity smart contracts
│       ├── src/             # Contract source files (19 contracts)
│       ├── scripts/         # Deploy scripts (Hardhat)
│       ├── artifacts/       # Compiled contract ABIs
│       ├── hardhat.config.js
│       └── package.json
├── sdk/                     # Python SDK
│   ├── ai_ml/              # AI/ML framework & scoring
│   ├── cli/                # CLI tool (mtcli)
│   ├── contracts/          # Smart contract ABIs & wrappers
│   ├── core/               # Core protocol logic
│   ├── keymanager/         # Wallet & key management
│   ├── polkadot/           # Polkadot Hub integration
│   ├── security/           # Security module
│   ├── tokenomics/         # Token economics
│   └── utils/              # Shared utilities
├── subnet/                  # Subnet demo (miner + validator)
├── demo/                    # Step-by-step demo scripts
├── docs/                    # Documentation
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

## 🎬 Demo Video (~5 minutes)

### 📹 How to Record

**Preparation:**

```bash
# 1. Clean task queue
rm -f subnet/task_queue/*.json

# 2. Start web frontend
cd web && npm run dev          # → http://localhost:3000

# 3. Prepare 2 terminal tabs (split screen) + browser with 4 tabs:
#    Tab 1: http://localhost:3000              (Subnets Hub)
#    Tab 2: http://localhost:3000/subnet/1     (Subnet Detail + Metagraph)
#    Tab 3: http://localhost:3000/tokenomics   (Yield Simulator)
#    Tab 4: Blockscout explorer                (SubnetRegistry contract)
```

**Scene-by-scene (9 scenes):**

| # | Time | Content | What to Show |
|---|------|---------|-------------|
| 1 | 0:00–0:40 | 🎯 Hook + Subnets Hub | Browser — BIOS animation → dashboard stats |
| 2 | 0:40–1:20 | 🧠 Subnet Detail | Click Subnet 1 → Metagraph table (11 nodes) |
| 3 | 1:20–1:50 | ✅ Validators | Navigate to Validators page |
| 4 | 1:50–2:20 | 💎 Tokenomics | Yield Simulator — drag sliders |
| 5 | 2:20–2:50 | 🌐 Blockscout | Show deployed contracts on explorer |
| 6 | 2:50–3:10 | ⛏️ Start Miner | Terminal: `python subnet/miner1.py` |
| 7 | 3:10–4:20 | 🔷 Validator Loop ⭐ | Terminal: `python subnet/validator1.py` → full epoch |
| 8 | 4:20–4:45 | 🔍 Verify | Blockscout TX + web frontend refresh |
| 9 | 4:45–5:10 | 🎯 Closing | Summary from Subnets Hub |

> 💡 Full narration script with voiceover text: **[DEMO_NARRATION_SCRIPT.py](DEMO_NARRATION_SCRIPT.py)**

### Running the Subnet Demo (Without Video)

```bash
# Terminal 1 — Miner
python subnet/miner1.py

# Terminal 2 — Validator
python subnet/validator1.py

# Full automated demo
cd demo && python 07_run_demo.py
```

See **[Demo Guide](demo/README.md)** for step-by-step instructions and **[Subnet Guide](subnet/README.md)** for running individual miners/validators.

---

## 📚 Documentation

* **[ModernTensor Whitepaper (Vietnamese)](MODERNTENSOR_WHITEPAPER_VI.md)** — Complete project whitepaper
* **[Whitepaper (English)](WHITEPAPER.md)** — English version
* **[How It Works (Vietnamese)](docs/HOW_IT_WORKS_VI.md)** — Technical deep-dive
* **[Non-Technical Overview (Vietnamese)](docs/NON_TECH_OVERVIEW_VI.md)** — For non-technical audience
* **[Pitch Deck](docs/PITCH_DECK.md)** — Project overview presentation
* **[Tokenomics](docs/TOKENOMICS.md)** — Token distribution and economics
* **[Roadmap](docs/ROADMAP.md)** — Development roadmap
* **[Security](SECURITY.md)** — Security model and policies

---

## 🤝 Contributing

We welcome contributions!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
