# ModernTensor Project Guidelines

> AI agent configuration file. Follow these rules when working on this project.

## 📁 Project Structure

```
moderntensor/
├── luxtensor/
│   └── contracts/      # Solidity smart contracts (Hardhat)
├── sdk/                # Python AI SDK
├── tests/              # Test suite
├── docs/               # Documentation
└── docker/             # Docker configs
```

## 🛠️ Commands

### Solidity (Smart Contracts)

```bash
cd luxtensor/contracts
npm install              # Install deps
npx hardhat compile      # Compile
npx hardhat test         # Tests
npx hardhat run scripts/deploy-polkadot.js --network polkadot_testnet  # Deploy
```

### Python (SDK)

```bash
pip install -e .         # Install dev mode
pytest                   # Tests
ruff check .             # Lint
mypy .                   # Type check
```

## 📝 Code Style

| Language | Formatter | Linter |
|----------|-----------|--------|
| Python | `black` | `ruff`, `mypy` |
| Solidity | `prettier` | `solhint` |

## 🏗️ Architecture

- **Clean Code**: SRP, DRY, KISS, YAGNI
- **Python**: Type hints required
- **Solidity**: Follow OpenZeppelin patterns

## ⚠️ Before Editing

1. **Understand context**: Read related files first
2. **Check dependencies**: Who imports this file?
3. **Run tests**: Verify changes don't break existing code
4. **Update docs**: Keep documentation in sync

## 🔐 Security

- Never commit secrets or API keys
- Use `.env` for environment variables
- Validate all inputs
- Follow OWASP guidelines for contracts

## 🧪 Testing

- Unit tests required for new functions
- Integration tests for cross-module features
- Target: 80%+ coverage

## 📚 Key Files

| File | Purpose |
|------|---------|
| `luxtensor/contracts/hardhat.config.js` | Hardhat + network config |
| `luxtensor/contracts/src/` | Solidity contracts |
| `sdk/pyproject.toml` | Python package config |
| `.env.example` | Environment template |
