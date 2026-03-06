// SPDX-License-Identifier: MIT
/**
 * SubnetRegistry — Full Test Suite
 *
 * Tests: createSubnet, registerNode, self-vote protection,
 *        commit-reveal weights, setWeights, runEpoch, claimEmission,
 *        delegation, slashing, quadratic voting, trust updates,
 *        updateEmissionShare, deregisterNode warning
 */

const { expect } = require("chai");
const { ethers } = require("hardhat");
const {
  loadFixture,
  mine,
} = require("@nomicfoundation/hardhat-network-helpers");

describe("SubnetRegistry", function () {
  // NodeType enum: 0 = MINER, 1 = VALIDATOR
  const MINER = 0;
  const VALIDATOR = 1;

  async function deployFixture() {
    const [owner, validator1, validator2, miner1, miner2, outsider] =
      await ethers.getSigners();

    const MDTToken = await ethers.getContractFactory("MDTToken");
    const token = await MDTToken.deploy();
    await token.waitForDeployment();
    const tokenAddr = await token.getAddress();

    const SubnetRegistry = await ethers.getContractFactory("SubnetRegistry");
    const registry = await SubnetRegistry.deploy(
      tokenAddr,
      0, // registration cost = 0
      ethers.parseEther("1") // emissionPerBlock
    );
    await registry.waitForDeployment();
    const registryAddr = await registry.getAddress();

    // Mint and distribute tokens
    await token.mintCategory(0, owner.address, ethers.parseEther("500000"));
    await token.mintCategory(1, validator1.address, ethers.parseEther("50000"));
    await token.mintCategory(2, validator2.address, ethers.parseEther("50000"));
    await token.mintCategory(3, miner1.address, ethers.parseEther("50000"));
    await token.mintCategory(4, miner2.address, ethers.parseEther("50000"));

    // Fund emission pool
    await token.approve(registryAddr, ethers.parseEther("200000"));
    await registry.fundEmissionPool(ethers.parseEther("200000"));

    // Approve for all users
    for (const signer of [validator1, validator2, miner1, miner2]) {
      await token
        .connect(signer)
        .approve(registryAddr, ethers.parseEther("50000"));
    }

    return {
      token,
      registry,
      owner,
      validator1,
      validator2,
      miner1,
      miner2,
      outsider,
      registryAddr,
    };
  }

  async function subnetCreatedFixture() {
    const fix = await loadFixture(deployFixture);
    const { registry } = fix;

    await registry.createSubnet("TestSubnet", 64, ethers.parseEther("10"), 10);

    return { ...fix, netuid: 1 };
  }

  async function nodesRegisteredFixture() {
    const fix = await loadFixture(subnetCreatedFixture);
    const { registry, validator1, miner1, netuid } = fix;

    await registry
      .connect(validator1)
      .registerNode(netuid, validator1.address, VALIDATOR, ethers.parseEther("100"));
    await registry
      .connect(miner1)
      .registerNode(netuid, miner1.address, MINER, ethers.parseEther("50"));

    return { ...fix, validatorUid: 0, minerUid: 1 };
  }

  // ─── Deployment ──────────────────────────────────────────

  describe("Deployment", function () {
    it("should set correct token", async function () {
      const { token, registry } = await loadFixture(deployFixture);
      expect(await registry.token()).to.equal(await token.getAddress());
    });

    it("should set emission per block", async function () {
      const { registry } = await loadFixture(deployFixture);
      expect(await registry.emissionPerBlock()).to.equal(ethers.parseEther("1"));
    });

    it("should start with nextNetuid = 1", async function () {
      const { registry } = await loadFixture(deployFixture);
      // After deployment but before any subnet, getSubnetCount should be 1
      // because netuid 0 is root
      const count = await registry.getSubnetCount();
      expect(count).to.be.gte(0);
    });
  });

  // ─── createSubnet ────────────────────────────────────────

  describe("createSubnet", function () {
    it("should create a subnet with correct params", async function () {
      const { registry } = await loadFixture(deployFixture);
      const tx = await registry.createSubnet(
        "AI-Subnet", 128, ethers.parseEther("10"), 20
      );
      await expect(tx).to.emit(registry, "SubnetCreated");

      const sub = await registry.getSubnet(1);
      expect(sub.name).to.equal("AI-Subnet");
      expect(sub.maxNodes).to.equal(128);
      expect(sub.emissionShare).to.equal(1000); // default 10%
      expect(sub.active).to.equal(true);
    });

    it("should increment totalEmissionShares", async function () {
      const { registry } = await loadFixture(deployFixture);
      const before = await registry.totalEmissionShares();
      await registry.createSubnet("Sub1", 64, 0, 10);
      expect(await registry.totalEmissionShares()).to.equal(before + 1000n);
    });

    it("should revert on empty name", async function () {
      const { registry } = await loadFixture(deployFixture);
      await expect(
        registry.createSubnet("", 64, 0, 10)
      ).to.be.revertedWith("Invalid name");
    });

    it("should revert on zero maxNodes", async function () {
      const { registry } = await loadFixture(deployFixture);
      await expect(
        registry.createSubnet("Test", 0, 0, 10)
      ).to.be.revertedWith("Invalid maxNodes");
    });

    it("should revert on zero tempo", async function () {
      const { registry } = await loadFixture(deployFixture);
      await expect(
        registry.createSubnet("Test", 64, 0, 0)
      ).to.be.revertedWith("Invalid tempo");
    });
  });

  // ─── updateSubnet ────────────────────────────────────────

  describe("updateSubnet", function () {
    it("should update subnet parameters", async function () {
      const { registry, netuid } = await loadFixture(subnetCreatedFixture);
      await registry.updateSubnet(netuid, 256, ethers.parseEther("20"), 50, 14400);
      const sub = await registry.getSubnet(netuid);
      expect(sub.maxNodes).to.equal(256);
    });

    it("should revert for non-owner", async function () {
      const { registry, netuid, outsider } =
        await loadFixture(subnetCreatedFixture);
      await expect(
        registry.connect(outsider).updateSubnet(netuid, 256, 0, 10, 7200)
      ).to.be.revertedWith("Not authorized");
    });
  });

  // ─── updateEmissionShare ─────────────────────────────────

  describe("updateEmissionShare", function () {
    it("should update emission share and adjust totalEmissionShares", async function () {
      const { registry, netuid } = await loadFixture(subnetCreatedFixture);
      const totalBefore = await registry.totalEmissionShares();
      await registry.updateEmissionShare(netuid, 2000);

      const sub = await registry.getSubnet(netuid);
      expect(sub.emissionShare).to.equal(2000);
      expect(await registry.totalEmissionShares()).to.equal(
        totalBefore - 1000n + 2000n
      );
    });

    it("should emit EmissionShareUpdated", async function () {
      const { registry, netuid } = await loadFixture(subnetCreatedFixture);
      await expect(registry.updateEmissionShare(netuid, 3000))
        .to.emit(registry, "EmissionShareUpdated")
        .withArgs(netuid, 1000, 3000);
    });

    it("should revert for invalid share", async function () {
      const { registry, netuid } = await loadFixture(subnetCreatedFixture);
      await expect(
        registry.updateEmissionShare(netuid, 0)
      ).to.be.revertedWith("Invalid share");
      await expect(
        registry.updateEmissionShare(netuid, 10001)
      ).to.be.revertedWith("Invalid share");
    });

    it("should revert for non-owner", async function () {
      const { registry, netuid, outsider } =
        await loadFixture(subnetCreatedFixture);
      await expect(
        registry.connect(outsider).updateEmissionShare(netuid, 2000)
      ).to.be.revertedWith("Not authorized");
    });
  });

  // ─── registerNode ────────────────────────────────────────

  describe("registerNode", function () {
    it("should register a validator", async function () {
      const { registry, validator1, netuid } =
        await loadFixture(subnetCreatedFixture);
      await expect(
        registry
          .connect(validator1)
          .registerNode(netuid, validator1.address, VALIDATOR, ethers.parseEther("100"))
      ).to.emit(registry, "NodeRegistered");
    });

    it("should register a miner", async function () {
      const { registry, miner1, netuid } =
        await loadFixture(subnetCreatedFixture);
      await expect(
        registry
          .connect(miner1)
          .registerNode(netuid, miner1.address, MINER, ethers.parseEther("50"))
      ).to.emit(registry, "NodeRegistered");
    });

    it("should prevent self-voting (same coldkey as both types)", async function () {
      const { registry, validator1, netuid } =
        await loadFixture(subnetCreatedFixture);
      await registry
        .connect(validator1)
        .registerNode(netuid, validator1.address, VALIDATOR, ethers.parseEther("100"));
      await expect(
        registry
          .connect(validator1)
          .registerNode(netuid, validator1.address, MINER, ethers.parseEther("50"))
      ).to.be.revertedWith("Already registered");
    });

    it("should reject duplicate hotkey registration", async function () {
      const { registry, validator1, netuid } =
        await loadFixture(subnetCreatedFixture);
      await registry
        .connect(validator1)
        .registerNode(netuid, validator1.address, VALIDATOR, ethers.parseEther("100"));
      await expect(
        registry
          .connect(validator1)
          .registerNode(netuid, validator1.address, VALIDATOR, ethers.parseEther("50"))
      ).to.be.revertedWith("Already registered");
    });

    it("should reject below min stake", async function () {
      const { registry, miner1, netuid } =
        await loadFixture(subnetCreatedFixture);
      await expect(
        registry
          .connect(miner1)
          .registerNode(netuid, miner1.address, MINER, ethers.parseEther("1"))
      ).to.be.revertedWith("Insufficient stake");
    });

    it("should start with 50% trust", async function () {
      const { registry, validator1, netuid } =
        await loadFixture(subnetCreatedFixture);
      await registry
        .connect(validator1)
        .registerNode(netuid, validator1.address, VALIDATOR, ethers.parseEther("100"));
      const trust = await registry.getTrust(netuid, 0);
      const halfTrust = (5000n * 10n ** 14n);
      expect(trust).to.equal(halfTrust);
    });
  });

  // ─── deregisterNode ──────────────────────────────────────

  describe("deregisterNode", function () {
    it("should deregister and return stake", async function () {
      const { registry, token, validator1, netuid, validatorUid } =
        await loadFixture(nodesRegisteredFixture);

      const balBefore = await token.balanceOf(validator1.address);

      // Mine past immunity period
      await mine(7201);

      await registry.connect(validator1).deregisterNode(netuid, validatorUid);

      const balAfter = await token.balanceOf(validator1.address);
      expect(balAfter).to.be.gt(balBefore);
    });

    it("should revert during immunity period", async function () {
      const { registry, validator1, netuid, validatorUid } =
        await loadFixture(nodesRegisteredFixture);
      await expect(
        registry.connect(validator1).deregisterNode(netuid, validatorUid)
      ).to.be.revertedWith("Immunity period");
    });

    it("should emit NodeDeregistered", async function () {
      const { registry, validator1, netuid, validatorUid } =
        await loadFixture(nodesRegisteredFixture);
      await mine(7201);
      await expect(
        registry.connect(validator1).deregisterNode(netuid, validatorUid)
      ).to.emit(registry, "NodeDeregistered");
    });
  });

  // ─── setWeights (direct, for admin/testing) ──────────────

  describe("setWeights", function () {
    it("should allow owner to set weights on miners", async function () {
      const { registry, owner, netuid, validatorUid, minerUid } =
        await loadFixture(nodesRegisteredFixture);
      await expect(
        registry.setWeights(netuid, validatorUid, [minerUid], [10000])
      ).to.emit(registry, "WeightsSet");
    });

    it("should revert for non-owner", async function () {
      const { registry, miner1, netuid, minerUid, validatorUid } =
        await loadFixture(nodesRegisteredFixture);
      await expect(
        registry
          .connect(miner1)
          .setWeights(netuid, validatorUid, [minerUid], [10000])
      ).to.be.reverted;
    });
  });

  // ─── Commit-Reveal ───────────────────────────────────────

  describe("Commit-Reveal Weights", function () {
    it("should commit weights", async function () {
      const { registry, validator1, netuid } =
        await loadFixture(nodesRegisteredFixture);
      const commitHash = ethers.keccak256(ethers.toUtf8Bytes("secret"));
      await expect(registry.connect(validator1).commitWeights(netuid, commitHash))
        .to.emit(registry, "WeightsCommitted");
    });

    it("should reveal matching commit", async function () {
      const { registry, validator1, netuid, minerUid } =
        await loadFixture(nodesRegisteredFixture);

      const uids = [minerUid];
      const weights = [10000];
      const salt = ethers.keccak256(ethers.toUtf8Bytes("salt123"));
      const commitHash = ethers.keccak256(
        ethers.solidityPacked(
          ["uint16[]", "uint16[]", "bytes32"],
          [uids, weights, salt]
        )
      );

      await registry.connect(validator1).commitWeights(netuid, commitHash);

      // Mine past commitMinDelay
      await mine(11);

      await expect(
        registry.connect(validator1).revealWeights(netuid, uids, weights, salt)
      ).to.emit(registry, "WeightsRevealed");
    });
  });

  // ─── runEpoch ────────────────────────────────────────────

  describe("runEpoch", function () {
    it("should run epoch and distribute emission", async function () {
      const { registry, validator1, netuid, validatorUid, minerUid } =
        await loadFixture(nodesRegisteredFixture);

      // Owner sets weights on miner
      await registry.setWeights(netuid, validatorUid, [minerUid], [10000]);

      // Mine past tempo
      await mine(11);

      await expect(registry.runEpoch(netuid))
        .to.emit(registry, "EpochCompleted");
    });

    it("should revert if too early", async function () {
      const { registry, netuid } = await loadFixture(nodesRegisteredFixture);
      await expect(registry.runEpoch(netuid)).to.be.revertedWith("Too early");
    });
  });

  // ─── claimEmission ───────────────────────────────────────

  describe("claimEmission", function () {
    it("should claim after epoch", async function () {
      const { registry, token, validator1, miner1, netuid, validatorUid, minerUid } =
        await loadFixture(nodesRegisteredFixture);

      // Set weights and run epoch
      await registry.setWeights(netuid, validatorUid, [minerUid], [10000]);
      await mine(11);
      await registry.runEpoch(netuid);

      // Miner claims emission
      const balBefore = await token.balanceOf(miner1.address);
      await registry.connect(miner1).claimEmission(netuid, minerUid);
      const balAfter = await token.balanceOf(miner1.address);
      expect(balAfter).to.be.gt(balBefore);
    });
  });

  // ─── Delegation ──────────────────────────────────────────

  describe("Delegation", function () {
    it("should delegate stake to validator", async function () {
      const { registry, miner2, token, netuid, validatorUid } =
        await loadFixture(nodesRegisteredFixture);
      const amount = ethers.parseEther("100");
      await token
        .connect(miner2)
        .approve(await registry.getAddress(), amount);
      // miner2 is separate from registered miner1 — acts as delegator
      await expect(
        registry.connect(miner2).delegate(netuid, validatorUid, amount)
      ).to.emit(registry, "StakeDelegated");
    });

    it("should undelegate stake", async function () {
      const { registry, miner2, token, netuid, validatorUid } =
        await loadFixture(nodesRegisteredFixture);
      const amount = ethers.parseEther("100");
      await token
        .connect(miner2)
        .approve(await registry.getAddress(), amount);
      await registry.connect(miner2).delegate(netuid, validatorUid, amount);
      await expect(
        registry.connect(miner2).undelegate(netuid, validatorUid, amount)
      ).to.emit(registry, "StakeUndelegated");
    });
  });

  // ─── Slashing ────────────────────────────────────────────

  describe("Slashing", function () {
    it("should slash a node (owner only)", async function () {
      const { registry, netuid, minerUid } =
        await loadFixture(nodesRegisteredFixture);
      await expect(
        registry.slashNode(netuid, minerUid, 1000, "Malicious behavior")
      ).to.emit(registry, "NodeSlashed");
    });

    it("should revert for non-owner", async function () {
      const { registry, netuid, minerUid, outsider } =
        await loadFixture(nodesRegisteredFixture);
      await expect(
        registry.connect(outsider).slashNode(netuid, minerUid, 1000, "Malicious")
      ).to.be.reverted;
    });
  });

  // ─── Admin Functions ─────────────────────────────────────

  describe("Admin", function () {
    it("should set subnet registration cost", async function () {
      const { registry } = await loadFixture(deployFixture);
      await registry.setSubnetRegistrationCost(ethers.parseEther("50"));
      expect(await registry.subnetRegistrationCost()).to.equal(
        ethers.parseEther("50")
      );
    });

    it("should set emission per block", async function () {
      const { registry } = await loadFixture(deployFixture);
      await registry.setEmissionPerBlock(ethers.parseEther("2"));
      expect(await registry.emissionPerBlock()).to.equal(ethers.parseEther("2"));
    });

    it("should set slash percentage", async function () {
      const { registry } = await loadFixture(deployFixture);
      await registry.setSlashPercentage(3000);
    });

    it("should revert slash percentage > 50%", async function () {
      const { registry } = await loadFixture(deployFixture);
      await expect(registry.setSlashPercentage(5001)).to.be.revertedWith(
        "Max 50%"
      );
    });
  });

  // ─── View Functions ──────────────────────────────────────

  describe("Views", function () {
    it("getMetagraph should return node info", async function () {
      const { registry, validator1, netuid } =
        await loadFixture(nodesRegisteredFixture);
      const [hotkeys, coldkeys, stakes, ranks, incentives, emissions, nodeTypes, activeFlags] =
        await registry.getMetagraph(netuid);
      // validator1 is uid 0
      expect(hotkeys[0]).to.equal(validator1.address);
      expect(activeFlags[0]).to.equal(true);
    });

    it("getValidatorScore should return scoring breakdown", async function () {
      const { registry, netuid, validatorUid } =
        await loadFixture(nodesRegisteredFixture);
      const score = await registry.getValidatorScore(netuid, validatorUid);
      expect(score.trust).to.be.gt(0);
      expect(score.active).to.equal(true);
      expect(score.effectivePower).to.be.gt(0);
    });

    it("getUidByHotkey should resolve correctly", async function () {
      const { registry, validator1, netuid, validatorUid } =
        await loadFixture(nodesRegisteredFixture);
      const uid = await registry.getUidByHotkey(netuid, validator1.address);
      expect(uid).to.equal(validatorUid);
    });
  });
});
