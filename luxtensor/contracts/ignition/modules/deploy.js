/**
 * Hardhat Ignition module for deploying all ModernTensor contracts.
 * Used with: npx hardhat ignition deploy ./ignition/modules/deploy.js --network polkadot_testnet
 */
const { buildModule } = require("@nomicfoundation/hardhat-ignition/modules");

module.exports = buildModule("ModernTensor", (m) => {
    // Phase 1: Core Token
    const mdtToken = m.contract("MDTToken");

    // Phase 2: Token Infrastructure
    const mdtVesting = m.contract("MDTVesting", [mdtToken]);
    const mdtStaking = m.contract("MDTStaking", [mdtToken]);

    // Phase 3: AI Infrastructure
    const zkmlVerifier = m.contract("ZkMLVerifier");
    const aiOracle = m.contract("AIOracle");

    // Phase 4: Subnet Registry
    const subnetRegistry = m.contract("SubnetRegistry", [mdtToken, mdtStaking]);

    return {
        mdtToken,
        mdtVesting,
        mdtStaking,
        zkmlVerifier,
        aiOracle,
        subnetRegistry,
    };
});
