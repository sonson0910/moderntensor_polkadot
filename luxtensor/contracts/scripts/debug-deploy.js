/**
 * Debug deploy: try multiple TX types and raw eth_sendTransaction
 * Usage: node scripts/debug-deploy.js
 */
const { ethers } = require("ethers");
const fs = require("fs");
require("dotenv").config();

const RPC_URL = "https://westend-asset-hub-eth-rpc.polkadot.io";
const CHAIN_ID = 420420421;

async function main() {
    const provider = new ethers.JsonRpcProvider(RPC_URL, {
        chainId: CHAIN_ID,
        name: "westend-assethub",
    });
    const wallet = new ethers.Wallet(process.env.PRIVATE_KEY, provider);
    const nonce = await provider.getTransactionCount(wallet.address);
    const feeData = await provider.getFeeData();

    console.log("Deployer:", wallet.address);
    console.log("Nonce:", nonce);
    console.log("Fee data:", JSON.stringify(feeData, (k, v) => typeof v === "bigint" ? v.toString() : v));

    // Check supported methods
    console.log("\n--- Checking RPC capabilities ---");
    try {
        const chainId = await provider.send("eth_chainId", []);
        console.log("eth_chainId:", chainId);
    } catch (e) {
        console.log("eth_chainId error:", e.message);
    }

    try {
        const netVersion = await provider.send("net_version", []);
        console.log("net_version:", netVersion);
    } catch (e) {
        console.log("net_version error:", e.message);
    }

    // Load SimpleStorage
    const artifact = JSON.parse(
        fs.readFileSync("artifacts/src/SimpleStorage.sol/SimpleStorage.json", "utf-8")
    );
    const bytecode = artifact.bytecode;
    console.log("\nBytecode length:", bytecode.length);

    // Try eth_call first to see if contract code works
    console.log("\n--- eth_call test (dry run) ---");
    try {
        const callResult = await provider.send("eth_call", [{
            from: wallet.address,
            data: bytecode,
            gas: "0x4C4B40",
        }, "latest"]);
        console.log("eth_call result length:", callResult.length);
        console.log("eth_call result prefix:", callResult.substring(0, 40));
    } catch (e) {
        console.log("eth_call error:", e.message?.substring(0, 300));
    }

    // Try estimateGas
    console.log("\n--- eth_estimateGas test ---");
    try {
        const gasEstimate = await provider.send("eth_estimateGas", [{
            from: wallet.address,
            data: bytecode,
        }]);
        console.log("Gas estimate:", gasEstimate);
    } catch (e) {
        console.log("eth_estimateGas error:", e.message?.substring(0, 300));
    }

    // Try manually signing and sending
    console.log("\n--- Manual TX build ---");
    const tx = {
        type: 2,
        chainId: CHAIN_ID,
        nonce: nonce,
        to: null,
        data: bytecode,
        gasLimit: 5_000_000n,
        maxFeePerGas: feeData.maxFeePerGas,
        maxPriorityFeePerGas: feeData.maxPriorityFeePerGas,
        value: 0n,
    };

    console.log("TX fields:", JSON.stringify(tx, (k, v) => typeof v === "bigint" ? v.toString() : (k === "data" ? v.substring(0, 20) + "..." : v)));

    const signedTx = await wallet.signTransaction(tx);
    console.log("Signed TX prefix:", signedTx.substring(0, 40));
    console.log("Signed TX length:", signedTx.length);

    // Send it
    console.log("\n--- Sending TX ---");
    try {
        const txHash = await provider.send("eth_sendRawTransaction", [signedTx]);
        console.log("✅ TX Hash:", txHash);

        // Wait for receipt
        console.log("Waiting for receipt...");
        let receipt = null;
        for (let i = 0; i < 30; i++) {
            await new Promise(r => setTimeout(r, 6000));
            receipt = await provider.getTransactionReceipt(txHash);
            if (receipt) break;
            console.log("  ...waiting (" + (i + 1) * 6 + "s)");
        }
        if (receipt) {
            console.log("✅ Receipt:", JSON.stringify(receipt, (k, v) => typeof v === "bigint" ? v.toString() : v));
        } else {
            console.log("⏱️ No receipt after 3 minutes");
        }
    } catch (e) {
        console.log("eth_sendRawTransaction error:", e.message?.substring(0, 500));
    }
}

main()
    .then(() => process.exit(0))
    .catch((err) => {
        console.error("Fatal:", err.message?.substring(0, 500));
        process.exit(1);
    });
