/**
 * Generate a new ETH-compatible wallet for Polkadot Westend testnet.
 * Outputs: private key, address, and faucet instructions.
 */
const { ethers } = require("ethers");

const wallet = ethers.Wallet.createRandom();

console.log("════════════════════════════════════════════════════");
console.log("🔑 NEW WALLET GENERATED for Westend AssetHub Testnet");
console.log("════════════════════════════════════════════════════");
console.log(`  Address:     ${wallet.address}`);
console.log(`  Private Key: ${wallet.privateKey}`);
console.log();
console.log("📋 Next steps:");
console.log(`  1. Wallet created → .env file will be auto-configured`);
console.log(`  2. Get WND tokens from: https://faucet.polkadot.io/westend?parachain=1000`);
console.log(`     Enter your ETH address: ${wallet.address}`);
console.log(`  3. Or use Polkadot.js apps to transfer from relay chain`);
console.log();

// Write .env file
const fs = require("fs");
const envContent = `# ============================================
# ModernTensor — Polkadot Westend Testnet
# ============================================
# Auto-generated on ${new Date().toISOString()}
# NEVER commit to version control!

# Deployer private key
PRIVATE_KEY=${wallet.privateKey}

# Polkadot Hub RPC endpoints
POLKADOT_TESTNET_RPC=https://westend-asset-hub-eth-rpc.polkadot.io
PASEO_RPC=https://testnet-paseo-asset-hub-eth-rpc.polkadot.io
POLKADOT_MAINNET_RPC=https://asset-hub-eth-rpc.polkadot.io
`;

fs.writeFileSync(".env", envContent);
console.log("✅ .env file created with private key");
console.log(`   Address: ${wallet.address}`);
