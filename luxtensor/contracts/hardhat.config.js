require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
    solidity: {
        version: "0.8.28",
        settings: {
            viaIR: true,
            optimizer: {
                enabled: true,
                runs: 200
            }
        }
    },
    networks: {
        // Default local network (standard EVM for tests)
        hardhat: {},
        // ============================================
        // Moonbase Alpha — Moonbeam Testnet (Polkadot parachain EVM)
        // ============================================
        moonbase: {
            url: "https://rpc.api.moonbase.moonbeam.network",
            chainId: 1287,
            accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
            timeout: 120000,
        },
        // ============================================
        // Polkadot Hub TestNet (requires resolc compiler)
        // ============================================
        polkadotTestnet: {
            url: "https://services.polkadothub-rpc.com/testnet",
            chainId: 420420417,
            accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
            timeout: 120000,
        },
        // Westend AssetHub (requires resolc compiler)
        westend: {
            url: process.env.POLKADOT_TESTNET_RPC || "https://westend-asset-hub-eth-rpc.polkadot.io",
            chainId: 420420421,
            accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
            timeout: 120000,
        },
    },
    paths: {
        sources: "./src",
        tests: "./test",
        cache: "./cache",
        artifacts: "./artifacts"
    }
};
