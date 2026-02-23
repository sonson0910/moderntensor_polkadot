/**
 * Test basic transfer on Westend AssetHub.
 * Sends 0.001 WND to self to verify the RPC endpoint accepts transactions.
 *
 * Usage: node scripts/test-transfer.js
 */
const { ethers } = require("ethers");
require("dotenv").config();

const RPC_URL = "https://westend-asset-hub-eth-rpc.polkadot.io";
const CHAIN_ID = 420420421;

async function main() {
    const provider = new ethers.JsonRpcProvider(RPC_URL, {
        chainId: CHAIN_ID,
        name: "westend-assethub",
    });
    const wallet = new ethers.Wallet(process.env.PRIVATE_KEY, provider);
    const balance = await provider.getBalance(wallet.address);
    const nonce = await provider.getTransactionCount(wallet.address);
    const feeData = await provider.getFeeData();

    console.log("Address:", wallet.address);
    console.log("Balance:", ethers.formatEther(balance), "WND");
    console.log("Nonce:", nonce);
    console.log("Chain ID:", CHAIN_ID, "(hex:", "0x" + CHAIN_ID.toString(16) + ")");
    console.log("Gas Price:", feeData.gasPrice?.toString());
    console.log("MaxFeePerGas:", feeData.maxFeePerGas?.toString());

    // Simple self-transfer
    console.log("\nSending 0.001 WND to self...");

    const tx = await wallet.sendTransaction({
        to: wallet.address,
        value: ethers.parseEther("0.001"),
        gasLimit: 21000n,
    });

    console.log("TX Hash:", tx.hash);
    console.log("Waiting for confirmation...");

    const receipt = await tx.wait(1);
    console.log("\n✅ Transfer confirmed!");
    console.log("Block:", receipt.blockNumber);
    console.log("Gas used:", receipt.gasUsed.toString());
    console.log("Subscan:", "https://assethub-westend.subscan.io/tx/" + tx.hash);
}

main()
    .then(() => process.exit(0))
    .catch((err) => {
        console.error("\n❌ Failed:", err.code || "UNKNOWN");
        console.error("Message:", (err.message || "").substring(0, 500));
        if (err.error) console.error("RPC Error:", JSON.stringify(err.error).substring(0, 300));
        process.exit(1);
    });
