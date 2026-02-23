# ModernTensor SDK — API Reference

## Core Modules

### `sdk.ai_ml` — AI/ML Framework

#### `sdk.ai_ml.agent` — AI Agent Framework
Build AI agents that interact with the ModernTensor protocol.

#### `sdk.ai_ml.scoring` — Model Scoring
Multi-dimensional quality scoring for AI model outputs.

#### `sdk.ai_ml.zkml` — Zero-Knowledge ML
Generate and verify zero-knowledge proofs for ML inference results.

#### `sdk.ai_ml.subnets` — Subnet Definitions
Define specialized AI validation subnets.

#### `sdk.ai_ml.models` — Model Registry
Register and manage AI/ML models.

#### `sdk.ai_ml.processors` — Data Processors
Pre/post-processing pipelines for AI data.

---

### `sdk.security` — Security Module

Authentication, rate limiting, IP filtering, and API protection.

### `sdk.tokenomics` — Token Economics

MDT token emission schedules, reward calculations, and staking bonuses.

### `sdk.keymanager` — Key Management

Wallet creation, BIP39 mnemonics, coldkey/hotkey derivation.

---

### Utilities

#### `sdk.utils`

| Function | Description |
|----------|-------------|
| `to_mdt(amount)` | Convert MDT to smallest unit |
| `from_mdt(amount)` | Convert smallest unit to MDT |
| `format_mdt(amount)` | Format amount for display |
| `validate_address(addr)` | Validate address format |
| `shorten_address(addr)` | Shorten for display |
| `shorten_hash(hash)` | Shorten hash for display |

#### Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `MDT_DECIMALS` | 18 | Token decimal places |
| `MDT_WEI_MULTIPLIER` | 10^18 | Wei conversion factor |

---

### `sdk.errors` — Error Types

| Error | Description |
|-------|-------------|
| `RpcError` | Base RPC error |
| `InsufficientFundsError` | Not enough balance |
| `InvalidSignatureError` | Bad signature |
| `GasLimitExceededError` | Gas too high |
| `RateLimitedError` | Rate limit hit |

### `sdk.core.cache` — Caching

| Class | Description |
|-------|-------------|
| `MemoryCache` | In-memory cache |
| `RedisCache` | Redis-backed cache |
| `@cached` | Decorator for caching |
