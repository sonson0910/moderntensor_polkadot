# ModernTensor Roadmap

**Last Updated: March 2026**

---

## Phase 1: Foundation (Q1 2026) ✅ **COMPLETED**

### Smart Contract Development
- [x] MDTToken (ERC-20) — 21M supply, 8 allocation categories
- [x] MDTVesting — Cliff + linear vesting schedules
- [x] MDTStaking — Time-lock staking with 10-100% bonus multipliers
- [x] ZkMLVerifier — On-chain zkML proof verification (STARK/Groth16)
- [x] AIOracle — AI request/fulfill oracle with payment
- [x] GradientAggregator — Federated learning (FedAvg on-chain)
- [x] TrainingEscrow — Reward distribution + stake slashing
- [x] SubnetRegistry — Full Yuma Consensus with quadratic voting

### Python SDK
- [x] Core SDK architecture (ai_ml, cli, contracts, core, keymanager, polkadot, security, tokenomics, utils)
- [x] Polkadot Hub integration via pallet-revive EVM
- [x] CLI tool (mtcli) for network operations
- [x] Key management and wallet system

### Documentation
- [x] Whitepaper (English + Vietnamese)
- [x] Pitch Deck
- [x] Technical documentation
- [x] Non-Technical overview

---

## Phase 2: Testnet Launch (Q2 2026) 🔄 **IN PROGRESS**

### Subnet Demo
- [x] Miner implementation (text generation inference)
- [x] Validator implementation (scoring + consensus)
- [x] Demo pipeline (deploy → register → mine → validate → consensus)
- [ ] Multi-subnet deployment on testnet
- [ ] Stress testing with 50+ concurrent miners

### Contract Deployment
- [x] Deploy to Polkadot Hub testnet (Westend AssetHub)
- [ ] Complete contract audit
- [ ] Gas optimization pass
- [ ] Deploy monitoring dashboard

### Network Infrastructure
- [ ] P2P gossip layer for miner-validator communication
- [ ] Automated epoch management
- [ ] Weight update batching for gas efficiency

---

## Phase 3: Mainnet Preparation (Q3-Q4 2026)

### Security
- [ ] Smart contract security audit (external firm)
- [ ] SDK security hardening
- [ ] Bug bounty program launch
- [ ] Penetration testing

### Ecosystem
- [ ] Developer SDK documentation portal
- [ ] Subnet template marketplace
- [ ] Third-party validator onboarding guide
- [ ] Integration guides for AI model providers

### Governance
- [ ] On-chain DAO deployment
- [ ] Proposal and voting system
- [ ] Parameter governance (emission rate, staking minimums)

---

## Phase 4: Mainnet & Growth (2027)

### Launch
- [ ] Mainnet deployment on Polkadot Hub
- [ ] Token Generation Event (TGE)
- [ ] Initial validator set bootstrapping
- [ ] Community mining launch

### Cross-chain
- [ ] XCM integration for cross-parachain AI services
- [ ] Bridge to Ethereum for MDT liquidity
- [ ] Integration with Polkadot DeFi protocols

### AI Capabilities
- [ ] Image generation subnet
- [ ] Code generation subnet
- [ ] Multi-modal AI subnet
- [ ] Fine-tuning marketplace

### Growth
- [ ] Strategic partnerships with AI compute providers
- [ ] University and research lab partnerships
- [ ] Developer grants program
- [ ] Community governance transition

---

## Long-term Vision (2028+)

- **Decentralized Model Training**: Federated learning at scale using GradientAggregator
- **AI Model Marketplace**: Buy, sell, and lease pre-trained models with zkML verification
- **Enterprise Solutions**: Private subnet deployments for enterprises
- **AGI Infrastructure**: Building toward a global, permissionless AI compute network

---

*See [WHITEPAPER.md](../WHITEPAPER.md) Section 11 for the complete roadmap details.*
