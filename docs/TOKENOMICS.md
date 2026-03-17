# ModernTensor Tokenomics

**Token: MDT (ModernTensor Token)**
**Standard: ERC-20 on Polkadot Hub (pallet-revive EVM)**

---

## Token Overview

| Parameter | Value |
|-----------|-------|
| Token Name | ModernTensor |
| Symbol | MDT |
| Total Supply | 21,000,000 MDT |
| Decimals | 18 |
| Standard | ERC-20 |
| Deployment | Polkadot Hub via pallet-revive |

---

## Token Allocation

| Category | Allocation | Amount | Vesting |
|----------|-----------|--------|---------|
| Mining Rewards | 40% | 8,400,000 MDT | Emitted per epoch |
| Ecosystem Fund | 15% | 3,150,000 MDT | 3-year linear vesting |
| Team & Advisors | 15% | 3,150,000 MDT | 1-year cliff + 2-year linear |
| Community Incentives | 10% | 2,100,000 MDT | Community governance |
| Treasury | 10% | 2,100,000 MDT | DAO-governed |
| Early Backers | 5% | 1,050,000 MDT | 6-month cliff + 1-year linear |
| Liquidity | 3% | 630,000 MDT | Unlocked at launch |
| Airdrops | 2% | 420,000 MDT | Various campaigns |

---

## Emission Schedule

ModernTensor uses a **halving-based emission model** similar to Bitcoin:

- **Epoch Duration**: 360 blocks (~72 minutes at 12s/block)
- **Initial Emission**: 1.0 MDT per block
- **Halving Interval**: Every 10,500,000 blocks (~4 years)
- **Emission Rate**: Decreasing over time to ensure scarcity

```
Year 1-4:   1.0 MDT/block  → ~2,100,000 MDT/year
Year 5-8:   0.5 MDT/block  → ~1,050,000 MDT/year
Year 9-12:  0.25 MDT/block → ~525,000 MDT/year
...
```

---

## Reward Distribution

### Per Epoch Distribution

Each epoch, rewards are distributed as follows:

| Recipient | Share | Description |
|-----------|-------|-------------|
| Miners | 60% | Based on performance scores |
| Validators | 30% | Based on stake and accuracy |
| Delegators | 10% | Based on staked amount |

### Yuma Consensus Scoring

Rewards are weighted by the **Enhanced Yuma Consensus** mechanism:

1. Validators score miner outputs (quality, latency, accuracy)
2. Scores are aggregated with stake-weighted voting
3. Final weights determine emission distribution
4. Anti-gaming mechanisms prevent collusion

---

## Staking Mechanism

### MDTStaking Contract

| Lock Period | Bonus Multiplier |
|-------------|-----------------|
| 30 days | 10% bonus |
| 90 days | 25% bonus |
| 180 days | 50% bonus |
| 365 days | 100% bonus |

### Slashing Conditions

- **Downtime**: -5% of stake per violation
- **Invalid results**: -10% of stake
- **Malicious behavior**: Up to 100% slash

---

## Token Utility

1. **Staking**: Required for validators (min 10,000 MDT) and miners
2. **Payment**: AI inference requests are paid in MDT
3. **Governance**: Vote on proposals, subnet parameters
4. **Subnet Creation**: Deposit required to create new subnets
5. **Fee Burning**: A portion of transaction fees are burned (deflationary)

---

## Smart Contracts

| Contract | Role |
|----------|------|
| `MDTToken.sol` | ERC-20 token with 8 allocation categories |
| `MDTVesting.sol` | Cliff + linear vesting schedules |
| `MDTStaking.sol` | Time-lock staking with bonus multipliers |
| `SubnetRegistry.sol` | Emission distribution via Yuma Consensus |
| `TrainingEscrow.sol` | Reward distribution + stake slashing |
| `AIOracle.sol` | Payment for AI requests |

---

*See [WHITEPAPER.md](../WHITEPAPER.md) Section 7 for complete tokenomics details.*
