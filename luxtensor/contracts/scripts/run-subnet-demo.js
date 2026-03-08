/**
 * ModernTensor Subnet Demo — Full Lifecycle
 * 
 * Runs: Generate wallets → Mint MDT → Create subnet → Register 2 miners + 3 validators
 *       → Set weights → Run epoch → Verify rewards
 *
 * Usage: node scripts/run-subnet-demo.js
 */
const { ethers } = require("ethers");
const fs = require("fs");
const path = require("path");
require("dotenv").config();

// ═══════════════════════════════════════════════════════
// Configuration
// ═══════════════════════════════════════════════════════
const RPC_URL = "https://services.polkadothub-rpc.com/testnet";
const PRIVATE_KEY = process.env.PRIVATE_KEY?.startsWith("0x")
    ? process.env.PRIVATE_KEY
    : `0x${process.env.PRIVATE_KEY}`;

// Deployed contract addresses
const CONTRACTS = JSON.parse(
    fs.readFileSync(path.join(__dirname, "..", "deployments-polkadot.json"), "utf8")
).contracts;

const GAS_OPTS = { gasPrice: 1000000000000n, gasLimit: 10000000n };

// ═══════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════

function loadAbi(contractName) {
    const artifactsDir = path.join(__dirname, "..", "artifacts", "src");
    function search(dir) {
        for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
            const p = path.join(dir, entry.name);
            if (entry.isDirectory()) { const r = search(p); if (r) return r; }
            else if (entry.name === `${contractName}.json`) {
                return JSON.parse(fs.readFileSync(p, "utf8")).abi;
            }
        }
        return null;
    }
    return search(artifactsDir);
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function waitTx(tx, label) {
    console.log(`  🔄 ${label}: ${tx.hash}`);
    const receipt = await tx.wait();
    console.log(`  ✅ Confirmed (gas: ${receipt.gasUsed})`);
    return receipt;
}

// ═══════════════════════════════════════════════════════
// Main
// ═══════════════════════════════════════════════════════

async function main() {
    const provider = new ethers.JsonRpcProvider(RPC_URL);
    const deployer = new ethers.Wallet(PRIVATE_KEY, provider);
    const deployerBalance = await provider.getBalance(deployer.address);

    console.log("═".repeat(60));
    console.log("🧠 ModernTensor Subnet Demo");
    console.log("═".repeat(60));
    console.log("Deployer:", deployer.address);
    console.log("PAS Balance:", ethers.formatEther(deployerBalance));
    console.log("MDTToken:", CONTRACTS.MDTToken);
    console.log("SubnetRegistry:", CONTRACTS.SubnetRegistry);
    console.log("═".repeat(60));

    // Load contracts
    const tokenAbi = loadAbi("MDTToken");
    const registryAbi = loadAbi("SubnetRegistry");
    const token = new ethers.Contract(CONTRACTS.MDTToken, tokenAbi, deployer);
    const registry = new ethers.Contract(CONTRACTS.SubnetRegistry, registryAbi, deployer);

    // ══════════════════════════════════════════════
    // Step 1: Generate wallets
    // ══════════════════════════════════════════════
    console.log("\n╔══ Step 1: Generate Wallets ══╗");

    // Due to self-vote protection, we need separate coldkeys for miners vs validators
    const minerColdkey = ethers.Wallet.createRandom().connect(provider);
    const validatorColdkey = ethers.Wallet.createRandom().connect(provider);

    // Miners use separate hotkeys
    const miner1Hotkey = ethers.Wallet.createRandom();
    const miner2Hotkey = ethers.Wallet.createRandom();

    // Validators use separate hotkeys
    const val1Hotkey = ethers.Wallet.createRandom();
    const val2Hotkey = ethers.Wallet.createRandom();
    const val3Hotkey = ethers.Wallet.createRandom();

    console.log("  Miner coldkey:", minerColdkey.address);
    console.log("    Miner 1 hotkey:", miner1Hotkey.address);
    console.log("    Miner 2 hotkey:", miner2Hotkey.address);
    console.log("  Validator coldkey:", validatorColdkey.address);
    console.log("    Validator 1 hotkey:", val1Hotkey.address);
    console.log("    Validator 2 hotkey:", val2Hotkey.address);
    console.log("    Validator 3 hotkey:", val3Hotkey.address);

    // ══════════════════════════════════════════════
    // Step 2: Fund wallets with PAS (for gas)
    // ══════════════════════════════════════════════
    console.log("\n╔══ Step 2: Fund Wallets with PAS ══╗");

    const pasFund = ethers.parseEther("20"); // 20 PAS each
    let tx;

    tx = await deployer.sendTransaction({ to: minerColdkey.address, value: pasFund, ...GAS_OPTS });
    await waitTx(tx, "Fund miner coldkey 20 PAS");

    tx = await deployer.sendTransaction({ to: validatorColdkey.address, value: pasFund, ...GAS_OPTS });
    await waitTx(tx, "Fund validator coldkey 20 PAS");

    // ══════════════════════════════════════════════
    // Step 3: Mint MDT tokens
    // ══════════════════════════════════════════════
    console.log("\n╔══ Step 3: Mint MDT Tokens ══╗");

    // Category enum: 0=EmissionRewards, 1=EcosystemGrants, ...
    const EMISSION_REWARDS = 0;
    const ECOSYSTEM_GRANTS = 1;

    // Mint emission pool to SubnetRegistry (for rewards)
    const emissionAmount = ethers.parseEther("1000000"); // 1M MDT for emission pool
    tx = await token.mintCategory(EMISSION_REWARDS, CONTRACTS.SubnetRegistry, emissionAmount, GAS_OPTS);
    await waitTx(tx, `Mint 1,000,000 MDT → SubnetRegistry (emission pool)`);

    // Mint tokens for deployer (subnet creation + distribution)
    const deployerMint = ethers.parseEther("10000");
    tx = await token.mintCategory(ECOSYSTEM_GRANTS, deployer.address, deployerMint, GAS_OPTS);
    await waitTx(tx, `Mint 10,000 MDT → Deployer`);

    console.log("  MDT Balance (deployer):", ethers.formatEther(await token.balanceOf(deployer.address)));
    console.log("  MDT Balance (registry):", ethers.formatEther(await token.balanceOf(CONTRACTS.SubnetRegistry)));

    // ══════════════════════════════════════════════
    // Step 4: Transfer MDT to miners/validators for staking
    // ══════════════════════════════════════════════
    console.log("\n╔══ Step 4: Transfer MDT to Wallets ══╗");

    const stakeTransfer = ethers.parseEther("1000"); // 1000 MDT each
    tx = await token.transfer(minerColdkey.address, stakeTransfer, GAS_OPTS);
    await waitTx(tx, "Transfer 1000 MDT → Miner coldkey");

    tx = await token.transfer(validatorColdkey.address, stakeTransfer, GAS_OPTS);
    await waitTx(tx, "Transfer 1000 MDT → Validator coldkey");

    // ══════════════════════════════════════════════
    // Step 5: Create Subnet
    // ══════════════════════════════════════════════
    console.log("\n╔══ Step 5: Create Subnet ══╗");

    // Check registration cost
    const regCost = await registry.subnetRegistrationCost();
    console.log("  Subnet registration cost:", ethers.formatEther(regCost), "MDT");

    // Approve MDT for subnet registration
    if (regCost > 0n) {
        tx = await token.approve(CONTRACTS.SubnetRegistry, regCost, GAS_OPTS);
        await waitTx(tx, "Approve MDT for subnet registration");
    }

    // Create subnet with tempo=1 for quick epoch test
    tx = await registry.createSubnet(
        "ModernTensor AI",  // name
        100,                // maxNodes
        ethers.parseEther("100"), // minStake = 100 MDT
        1,                  // tempo = 1 block (instant epoch)
        GAS_OPTS
    );
    const createReceipt = await waitTx(tx, "Create subnet");

    // Parse netuid from event
    const createEvent = createReceipt.logs.find(
        l => l.address.toLowerCase() === CONTRACTS.SubnetRegistry.toLowerCase()
    );
    const netuid = 1; // First subnet after root (0)
    console.log("  🌐 Subnet created: netuid =", netuid);

    // ══════════════════════════════════════════════
    // Step 6: Register 2 Miners
    // ══════════════════════════════════════════════
    console.log("\n╔══ Step 6: Register 2 Miners ══╗");

    const minStake = ethers.parseEther("100");
    const tokenAsMiner = new ethers.Contract(CONTRACTS.MDTToken, tokenAbi, minerColdkey);
    const registryAsMiner = new ethers.Contract(CONTRACTS.SubnetRegistry, registryAbi, minerColdkey);

    // Approve MDT for both miners' stake
    tx = await tokenAsMiner.approve(CONTRACTS.SubnetRegistry, minStake * 2n, GAS_OPTS);
    await waitTx(tx, "Miner coldkey approves 200 MDT total");

    // Register miner 1
    tx = await registryAsMiner.registerNode(
        netuid, miner1Hotkey.address, 0, minStake, GAS_OPTS // 0 = MINER
    );
    await waitTx(tx, `Register Miner 1 (hotkey: ${miner1Hotkey.address.slice(0, 10)}...)`);

    // Register miner 2
    tx = await registryAsMiner.registerNode(
        netuid, miner2Hotkey.address, 0, minStake, GAS_OPTS // 0 = MINER
    );
    await waitTx(tx, `Register Miner 2 (hotkey: ${miner2Hotkey.address.slice(0, 10)}...)`);

    // ══════════════════════════════════════════════
    // Step 7: Register 3 Validators  
    // ══════════════════════════════════════════════
    console.log("\n╔══ Step 7: Register 3 Validators ══╗");

    const tokenAsVal = new ethers.Contract(CONTRACTS.MDTToken, tokenAbi, validatorColdkey);
    const registryAsVal = new ethers.Contract(CONTRACTS.SubnetRegistry, registryAbi, validatorColdkey);

    // Approve MDT for 3 validators' stake
    tx = await tokenAsVal.approve(CONTRACTS.SubnetRegistry, minStake * 3n, GAS_OPTS);
    await waitTx(tx, "Validator coldkey approves 300 MDT total");

    // Register validator 1
    tx = await registryAsVal.registerNode(
        netuid, val1Hotkey.address, 1, minStake, GAS_OPTS // 1 = VALIDATOR
    );
    await waitTx(tx, `Register Validator 1 (hotkey: ${val1Hotkey.address.slice(0, 10)}...)`);

    // Register validator 2
    tx = await registryAsVal.registerNode(
        netuid, val2Hotkey.address, 1, minStake, GAS_OPTS // 1 = VALIDATOR
    );
    await waitTx(tx, `Register Validator 2 (hotkey: ${val2Hotkey.address.slice(0, 10)}...)`);

    // Register validator 3
    tx = await registryAsVal.registerNode(
        netuid, val3Hotkey.address, 1, minStake, GAS_OPTS // 1 = VALIDATOR
    );
    await waitTx(tx, `Register Validator 3 (hotkey: ${val3Hotkey.address.slice(0, 10)}...)`);

    // ══════════════════════════════════════════════
    // Step 8: Set Weights (Owner sets weights for validators)
    // ══════════════════════════════════════════════
    console.log("\n╔══ Step 8: Set Weights ══╗");

    // Get UIDs
    const miner1Uid = await registry.hotkeyToUid(netuid, miner1Hotkey.address);
    const miner2Uid = await registry.hotkeyToUid(netuid, miner2Hotkey.address);
    const val1Uid = await registry.hotkeyToUid(netuid, val1Hotkey.address);
    const val2Uid = await registry.hotkeyToUid(netuid, val2Hotkey.address);
    const val3Uid = await registry.hotkeyToUid(netuid, val3Hotkey.address);

    console.log("  UIDs — Miner1:", miner1Uid, "Miner2:", miner2Uid);
    console.log("  UIDs — Val1:", val1Uid, "Val2:", val2Uid, "Val3:", val3Uid);

    // Validator 1: equal weights [500, 500]
    tx = await registry.setWeights(
        netuid, val1Uid,
        [miner1Uid, miner2Uid],
        [500, 500],
        GAS_OPTS
    );
    await waitTx(tx, "Validator 1 weights: [500, 500] (equal)");

    // Validator 2: favors miner 1 [700, 300]
    tx = await registry.setWeights(
        netuid, val2Uid,
        [miner1Uid, miner2Uid],
        [700, 300],
        GAS_OPTS
    );
    await waitTx(tx, "Validator 2 weights: [700, 300] (favors M1)");

    // Validator 3: favors miner 2 [300, 700]
    tx = await registry.setWeights(
        netuid, val3Uid,
        [miner1Uid, miner2Uid],
        [300, 700],
        GAS_OPTS
    );
    await waitTx(tx, "Validator 3 weights: [300, 700] (favors M2)");

    // ══════════════════════════════════════════════
    // Step 9: Wait and Run Epoch
    // ══════════════════════════════════════════════
    console.log("\n╔══ Step 9: Run Epoch ══╗");

    // Wait a few seconds for blocks to pass
    console.log("  ⏳ Waiting 15 seconds for blocks to pass...");
    await sleep(15000);

    // Check subnet state before epoch
    const subnet = await registry.subnets(netuid);
    console.log("  Subnet tempo:", subnet.tempo.toString());
    console.log("  Last epoch block:", subnet.lastEpochBlock.toString());
    console.log("  Current block:", (await provider.getBlockNumber()).toString());
    console.log("  Emission per block:", ethers.formatEther(await registry.emissionPerBlock()));

    // Check emission balances before
    console.log("\n  📊 Before epoch:");
    for (const [name, uid] of [["Miner1", miner1Uid], ["Miner2", miner2Uid], ["Val1", val1Uid], ["Val2", val2Uid], ["Val3", val3Uid]]) {
        const node = await registry.nodes(netuid, uid);
        console.log(`    ${name} (uid=${uid}): emission=${ethers.formatEther(node.emission)} MDT, trust=${node.trust.toString()}`);
    }

    // Run epoch!
    tx = await registry.runEpoch(netuid, GAS_OPTS);
    await waitTx(tx, "🚀 RUN EPOCH");

    // ══════════════════════════════════════════════
    // Step 10: Verify Rewards
    // ══════════════════════════════════════════════
    console.log("\n╔══ Step 10: Verify Rewards ══╗");

    console.log("  📊 After epoch:");
    for (const [name, uid] of [["Miner1", miner1Uid], ["Miner2", miner2Uid], ["Val1", val1Uid], ["Val2", val2Uid], ["Val3", val3Uid]]) {
        const node = await registry.nodes(netuid, uid);
        console.log(`    ${name} (uid=${uid}): emission=${ethers.formatEther(node.emission)} MDT, rank=${node.rank.toString()}, trust=${node.trust.toString()}`);
    }

    // ══════════════════════════════════════════════
    // Step 11: Claim Rewards
    // ══════════════════════════════════════════════
    console.log("\n╔══ Step 11: Claim Rewards ══╗");

    // Miners claim
    for (const [name, uid] of [["Miner1", miner1Uid], ["Miner2", miner2Uid]]) {
        const node = await registry.nodes(netuid, uid);
        if (node.emission > 0n) {
            const claimTx = await registryAsMiner.claimEmission(netuid, uid, GAS_OPTS);
            await waitTx(claimTx, `${name} claims ${ethers.formatEther(node.emission)} MDT`);
        } else {
            console.log(`  ${name}: no emission to claim`);
        }
    }

    // Validators claim
    for (const [name, uid] of [["Val1", val1Uid], ["Val2", val2Uid], ["Val3", val3Uid]]) {
        const node = await registry.nodes(netuid, uid);
        if (node.emission > 0n) {
            const claimTx = await registryAsVal.claimEmission(netuid, uid, GAS_OPTS);
            await waitTx(claimTx, `${name} claims ${ethers.formatEther(node.emission)} MDT`);
        } else {
            console.log(`  ${name}: no emission to claim`);
        }
    }

    // ══════════════════════════════════════════════
    // Final Summary
    // ══════════════════════════════════════════════
    console.log("\n" + "═".repeat(60));
    console.log("🎉 SUBNET DEMO COMPLETE!");
    console.log("═".repeat(60));
    console.log("\n  MDT Balances after claiming:");
    console.log("    Miner coldkey:", ethers.formatEther(await token.balanceOf(minerColdkey.address)), "MDT");
    console.log("    Validator coldkey:", ethers.formatEther(await token.balanceOf(validatorColdkey.address)), "MDT");
    console.log("    SubnetRegistry:", ethers.formatEther(await token.balanceOf(CONTRACTS.SubnetRegistry)), "MDT");
    console.log("\n  PAS remaining (deployer):", ethers.formatEther(await provider.getBalance(deployer.address)));

    // Save demo results
    const results = {
        timestamp: new Date().toISOString(),
        network: "polkadot_hub_testnet",
        netuid,
        wallets: {
            deployer: deployer.address,
            minerColdkey: minerColdkey.address,
            minerColdkeyPK: minerColdkey.privateKey,
            validatorColdkey: validatorColdkey.address,
            validatorColdkeyPK: validatorColdkey.privateKey,
        },
        nodes: {
            miner1: { hotkey: miner1Hotkey.address, uid: Number(miner1Uid) },
            miner2: { hotkey: miner2Hotkey.address, uid: Number(miner2Uid) },
            validator1: { hotkey: val1Hotkey.address, uid: Number(val1Uid) },
            validator2: { hotkey: val2Hotkey.address, uid: Number(val2Uid) },
            validator3: { hotkey: val3Hotkey.address, uid: Number(val3Uid) },
        },
    };
    fs.writeFileSync(
        path.join(__dirname, "..", "demo-results.json"),
        JSON.stringify(results, null, 2)
    );
    console.log("\n📁 Demo results saved to demo-results.json");
}

main()
    .then(() => process.exit(0))
    .catch((err) => {
        console.error("\n❌ Failed:", err.message?.substring(0, 800) || err);
        process.exit(1);
    });
