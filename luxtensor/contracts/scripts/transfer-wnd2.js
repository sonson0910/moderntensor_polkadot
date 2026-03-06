/**
 * Transfer WND on Westend Asset Hub — EIP-1559 with explicit params
 */
const hre = require("hardhat");

async function main() {
    const provider = new hre.ethers.JsonRpcProvider(
        "https://westend-asset-hub-eth-rpc.polkadot.io",
        { chainId: 420420421, name: "westend" }
    );

    const minerKey = "0x2191a9482334c6dcd94d58e5a0d929037c77b990d8a259fbb009a9812305da72";
    const miner = new hre.ethers.Wallet(minerKey, provider);

    const deployer = "0x350EB21005e911f4493a93449DDD329dE1fd7964";
    const validator = "0x7453dc226c58C5758eDd9De79162Fe2aeFDf229D";

    const bal = await provider.getBalance(miner.address);
    console.log("Miner balance:", hre.ethers.formatEther(bal), "WND");
    console.log("Nonce:", await provider.getTransactionCount(miner.address));

    // Get latest block for base fee
    const block = await provider.getBlock("latest");
    console.log("Latest block:", block.number, "baseFeePerGas:", block.baseFeePerGas?.toString());

    // Approach 1: type 2 EIP-1559 with explicit gasLimit
    console.log("\n--- Approach 1: EIP-1559 type 2 ---");
    try {
        const nonce = await provider.getTransactionCount(miner.address);
        const tx = {
            type: 2,
            to: deployer,
            value: hre.ethers.parseEther("6"),
            chainId: 420420421,
            nonce: nonce,
            maxFeePerGas: 220000000n,
            maxPriorityFeePerGas: 20000000n,
            gasLimit: 21000n,
        };
        const signed = await miner.signTransaction(tx);
        console.log("Signed TX (first 100 chars):", signed.substring(0, 100));
        const response = await provider.broadcastTransaction(signed);
        console.log("TX hash:", response.hash);
        const receipt = await response.wait();
        console.log("✅ Success! Gas used:", receipt.gasUsed.toString());
    } catch (e) {
        console.error("❌ Approach 1 failed:", e.message?.substring(0, 300) || e);
    }

    // Approach 2: type 0 legacy with exact gas price
    console.log("\n--- Approach 2: Legacy type 0 ---");
    try {
        const nonce = await provider.getTransactionCount(miner.address);
        const tx = {
            type: 0,
            to: deployer,
            value: hre.ethers.parseEther("6"),
            chainId: 420420421,
            nonce: nonce,
            gasPrice: 100000000n,
            gasLimit: 21000n,
        };
        const signed = await miner.signTransaction(tx);
        const response = await provider.broadcastTransaction(signed);
        console.log("TX hash:", response.hash);
        const receipt = await response.wait();
        console.log("✅ Success! Gas used:", receipt.gasUsed.toString());
    } catch (e) {
        console.error("❌ Approach 2 failed:", e.message?.substring(0, 300) || e);
    }

    // Approach 3: type 2 with higher gas limit
    console.log("\n--- Approach 3: EIP-1559 high gas ---");
    try {
        const nonce = await provider.getTransactionCount(miner.address);
        const tx = {
            type: 2,
            to: deployer,
            value: hre.ethers.parseEther("6"),
            chainId: 420420421,
            nonce: nonce,
            maxFeePerGas: 500000000n,
            maxPriorityFeePerGas: 100000000n,
            gasLimit: 500000n,
        };
        const signed = await miner.signTransaction(tx);
        const response = await provider.broadcastTransaction(signed);
        console.log("TX hash:", response.hash);
        const receipt = await response.wait();
        console.log("✅ Success! Gas used:", receipt.gasUsed.toString());
    } catch (e) {
        console.error("❌ Approach 3 failed:", e.message?.substring(0, 300) || e);
    }

    // Final balances
    console.log("\n=== Final Balances ===");
    console.log("Deployer: ", hre.ethers.formatEther(await provider.getBalance(deployer)), "WND");
    console.log("Validator:", hre.ethers.formatEther(await provider.getBalance(validator)), "WND");
    console.log("Miner:    ", hre.ethers.formatEther(await provider.getBalance(miner.address)), "WND");
}

main().catch(console.error);
