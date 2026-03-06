/**
 * Transfer WND on Westend Asset Hub via ethers.js
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

    console.log("Chain ID:", (await provider.getNetwork()).chainId.toString());
    console.log("Miner:", miner.address);
    console.log("Miner balance:", hre.ethers.formatEther(await provider.getBalance(miner.address)), "WND");

    // Get fee data
    const feeData = await provider.getFeeData();
    console.log("Fee data:", {
        gasPrice: feeData.gasPrice?.toString(),
        maxFeePerGas: feeData.maxFeePerGas?.toString(),
        maxPriorityFeePerGas: feeData.maxPriorityFeePerGas?.toString(),
    });

    // Transfer 6 WND to Deployer
    console.log("\n--- Transfer 6 WND to Deployer ---");
    try {
        const tx1 = await miner.sendTransaction({
            to: deployer,
            value: hre.ethers.parseEther("6"),
        });
        console.log("TX hash:", tx1.hash);
        const receipt1 = await tx1.wait();
        console.log("✅ Status:", receipt1.status === 1 ? "Success" : "Failed");
        console.log("   Gas used:", receipt1.gasUsed.toString());
    } catch (e) {
        console.error("❌ Transfer to deployer failed:", e.message.substring(0, 200));

        // Try with explicit params
        try {
            console.log("\nRetrying with explicit gas params...");
            const nonce = await provider.getTransactionCount(miner.address);
            const tx1b = await miner.sendTransaction({
                to: deployer,
                value: hre.ethers.parseEther("6"),
                gasLimit: 100000,
                gasPrice: feeData.gasPrice || 1000000000n,
                nonce: nonce,
                type: 0,
            });
            console.log("TX hash:", tx1b.hash);
            const receipt1b = await tx1b.wait();
            console.log("✅ Status:", receipt1b.status === 1 ? "Success" : "Failed");
        } catch (e2) {
            console.error("❌ Retry also failed:", e2.message.substring(0, 200));
        }
    }

    // Transfer 2 WND to Validator
    console.log("\n--- Transfer 2 WND to Validator ---");
    try {
        const tx2 = await miner.sendTransaction({
            to: validator,
            value: hre.ethers.parseEther("2"),
        });
        console.log("TX hash:", tx2.hash);
        const receipt2 = await tx2.wait();
        console.log("✅ Status:", receipt2.status === 1 ? "Success" : "Failed");
    } catch (e) {
        console.error("❌ Transfer to validator failed:", e.message.substring(0, 200));
    }

    // Final balances
    console.log("\n=== Final Balances ===");
    console.log("Deployer: ", hre.ethers.formatEther(await provider.getBalance(deployer)), "WND");
    console.log("Validator:", hre.ethers.formatEther(await provider.getBalance(validator)), "WND");
    console.log("Miner:    ", hre.ethers.formatEther(await provider.getBalance(miner.address)), "WND");
}

main().catch(console.error);
