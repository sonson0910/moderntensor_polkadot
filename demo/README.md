# 🚀 ModernTensor — Complete Subnet Demo

**Polkadot Solidity Hackathon 2026 — Track 1: EVM Smart Contract — AI-powered dApps**

Hệ thống demo hoàn chỉnh cho ModernTensor subnet trên Polkadot EVM, bao gồm đăng ký key, faucet, tạo subnet, đăng ký miner/validator và chạy full lifecycle.

## 📋 Tổng quan

| Script | Mô tả |
|--------|--------|
| `01_deploy_setup.py` | Deploy 8 contracts + khởi tạo (TGE, zkML, Oracle) |
| `02_register_keys.py` | Tạo/load ví cho deployer, validator, miner |
| `03_faucet.py` | Nhận token + phân phối MDT |
| `04_register_subnet.py` | Đăng ký validator + miner lên subnet |
| `05_run_miner.py` | Miner node — AI inference & zkML proof |
| `06_run_validator.py` | Validator node — task, evaluation, weights |
| `07_run_demo.py` | 🎯 **Chạy toàn bộ** — 5 phases, all 8 contracts |

## ⚡ Quick Start (3 lệnh)

```bash
# Terminal 1: Khởi động Hardhat node
cd luxtensor/contracts && npx hardhat node

# Terminal 2: Deploy contracts
cd luxtensor/contracts && npx hardhat run scripts/deploy-polkadot.js --network luxtensor_local

# Terminal 3: Chạy demo hoàn chỉnh
python demo/07_run_demo.py
```

## 📖 Chi tiết từng bước

### Bước 1: Deploy & Setup
```bash
python demo/01_deploy_setup.py
```
- Compile & deploy 8 smart contracts lên Hardhat node
- Chạy TGE (Token Generation Event) — mint MDT token
- Enable zkML dev mode
- Trust 3 AI model images (NLP, Finance, Code Review)
- Approve 3 models trong Oracle
- Tạo subnet + fund emission pool

### Bước 2: Register Keys
```bash
python demo/02_register_keys.py
```
- Local: dùng 3 Hardhat default accounts (auto-funded 10,000 ETH)
- Testnet: tự generate ví mới, lưu vào `wallets.json`
- Kiểm tra ETH + MDT balance

### Bước 3: Faucet & Token Distribution
```bash
python demo/03_faucet.py
```
- Mint MDT qua TGE (nếu chưa có)
- Phân phối: 5,000 MDT → validator, 1,000 MDT → miner
- Hiển thị bảng balance

### Bước 4: Register trên Subnet
```bash
python demo/04_register_subnet.py
```
- Validator stake 100 MDT, đăng ký `NodeType.VALIDATOR`
- Miner stake 50 MDT, đăng ký `NodeType.MINER`
- Đăng ký miner là Oracle fulfiller
- Hiển thị metagraph

### Bước 5: Chạy Miner (standalone)
```bash
python demo/05_run_miner.py
```
- AI inference engine (simulated NLP, Finance, Code domains)
- zkML proof generation (dev mode)
- Oracle task fulfillment
- Emission claiming

### Bước 6: Chạy Validator (standalone)
```bash
python demo/06_run_validator.py
```
- Tạo multi-domain AI tasks qua Oracle
- Đánh giá kết quả miner (quality + proof)
- Set weights on-chain (commit-reveal)
- Trigger epoch emission

### Bước 7: 🎯 Demo Hoàn Chỉnh
```bash
python demo/07_run_demo.py
```
Chạy tất cả 5 phases:
1. **Setup** — Connect, wallets, tokens, subnet, registration
2. **AI Cycle** — zkML setup, 3 tasks (NLP/Finance/Code), process, evaluate, weights
3. **Emission** — Fund pool, run epoch, claim rewards
4. **Federated Learning** — 3-round FedAvg training job
5. **Training Escrow** — Stake-gated training, validate, claim

## 🏗️ Architecture

```
8 Smart Contracts:
┌─────────────────────────────────────────────┐
│  MDTToken ─── MDTVesting ─── MDTStaking     │
│  SubnetRegistry ─── ZkMLVerifier            │
│  AIOracle ─── GradientAggregator            │
│  TrainingEscrow                             │
└─────────────────────────────────────────────┘

Lifecycle Flow:
  Token Mint (TGE) → Distribute → Create Subnet
  → Register Validator/Miner → Create AI Tasks
  → Process Inference → Generate zkML Proof
  → Verify Proof → Evaluate Quality → Set Weights
  → Run Epoch → Claim Emission → Federated Learning
  → Training Escrow
```

## 🌐 Networks

| Network | RPC | Chain ID |
|---------|-----|----------|
| Local (Hardhat) | `http://127.0.0.1:8545` | 31337 |
| Polkadot Testnet | `https://services.polkadothub-rpc.com/testnet` | 420420417 |
| Westend | `https://westend-asset-hub-eth-rpc.polkadot.io` | 420420421 |

Chuyển mạng:
```bash
NETWORK=polkadot_testnet python demo/07_run_demo.py
```

## 🔑 Accounts (Local Hardhat)

| Role | Address | ETH |
|------|---------|-----|
| Deployer | `0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266` | 10,000 |
| Validator | `0x70997970C51812dc3A010C7d01b50e0d17dc79C8` | 10,000 |
| Miner | `0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC` | 10,000 |

## 📊 Environment Variables

| Variable | Default | Mô tả |
|----------|---------|--------|
| `NETWORK` | `local` | Target network |
| `NETUID` | `1` | Subnet ID |
| `PRIVATE_KEY` | Hardhat account | Custom private key |
| `MAX_ROUNDS` | `0` (infinite) | Miner polling rounds |

## 🛠️ Troubleshooting

**"Cannot connect"** → Kiểm tra Hardhat node đang chạy:
```bash
cd luxtensor/contracts && npx hardhat node
```

**"Deployment file not found"** → Deploy contracts:
```bash
cd luxtensor/contracts && npx hardhat run scripts/deploy-polkadot.js --network luxtensor_local
```

**"Insufficient MDT"** → Chạy faucet:
```bash
python demo/03_faucet.py
```

**"Not registered"** → Đăng ký trước:
```bash
python demo/04_register_subnet.py
```
