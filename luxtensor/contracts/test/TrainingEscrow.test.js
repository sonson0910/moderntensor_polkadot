// SPDX-License-Identifier: MIT
/**
 * TrainingEscrow — Full Role-Based Tests
 *
 * Roles tested:
 *   - Owner/Deployer: validates trainers, completes tasks, sets slash rate, withdraws slashed
 *   - Task Creator: creates tasks, cancels tasks
 *   - Trainer A/B/C: joins tasks (stakes), submits results, claims rewards
 *   - Outsider: tries unauthorized actions (should revert)
 */

const { expect } = require("chai");
const { ethers } = require("hardhat");
const {
  loadFixture,
  time,
} = require("@nomicfoundation/hardhat-network-helpers");

describe("TrainingEscrow", function () {
  // ─── Fixtures ────────────────────────────────────────────

  async function deployFixture() {
    const [owner, taskCreator, trainerA, trainerB, trainerC, outsider] =
      await ethers.getSigners();

    // Deploy MDTToken
    const MDTToken = await ethers.getContractFactory("MDTToken");
    const token = await MDTToken.deploy();
    await token.waitForDeployment();

    // Mint tokens to participants
    await token.mintCategory(0, taskCreator.address, ethers.parseEther("100000"));  // EmissionRewards
    await token.mintCategory(1, trainerA.address, ethers.parseEther("50000"));       // EcosystemGrants
    await token.mintCategory(2, trainerB.address, ethers.parseEther("50000"));       // TeamCoreDev
    await token.mintCategory(3, trainerC.address, ethers.parseEther("50000"));       // PrivateSale

    // Deploy TrainingEscrow with 50% slash rate
    const TrainingEscrow = await ethers.getContractFactory("TrainingEscrow");
    const escrow = await TrainingEscrow.deploy(await token.getAddress(), 5000);
    await escrow.waitForDeployment();

    // Common test values
    const modelHash = ethers.keccak256(ethers.toUtf8Bytes("gpt-finetune-v1"));
    const resultHashA = ethers.keccak256(ethers.toUtf8Bytes("result-trainer-A"));
    const resultHashB = ethers.keccak256(ethers.toUtf8Bytes("result-trainer-B"));
    const resultHashC = ethers.keccak256(ethers.toUtf8Bytes("result-trainer-C"));

    return {
      token, escrow,
      owner, taskCreator, trainerA, trainerB, trainerC, outsider,
      modelHash, resultHashA, resultHashB, resultHashC,
    };
  }

  async function taskCreatedFixture() {
    const fix = await loadFixture(deployFixture);
    const { token, escrow, taskCreator, modelHash } = fix;

    // Creator approves + creates task
    const reward = ethers.parseEther("1000");
    const minStake = ethers.parseEther("100");
    await token.connect(taskCreator).approve(await escrow.getAddress(), reward);
    await escrow.connect(taskCreator).createTask(
      modelHash,
      reward,
      minStake,
      5,      // max trainers
      86400   // 24 hours
    );

    return { ...fix, reward, minStake, taskId: 0 };
  }

  async function trainersJoinedFixture() {
    const fix = await loadFixture(taskCreatedFixture);
    const { token, escrow, trainerA, trainerB, minStake } = fix;

    const stakeAmount = ethers.parseEther("200");

    // Trainer A joins
    await token.connect(trainerA).approve(await escrow.getAddress(), stakeAmount);
    await escrow.connect(trainerA).joinTask(0, stakeAmount);

    // Trainer B joins
    await token.connect(trainerB).approve(await escrow.getAddress(), stakeAmount);
    await escrow.connect(trainerB).joinTask(0, stakeAmount);

    return { ...fix, stakeAmount };
  }

  async function resultsSubmittedFixture() {
    const fix = await loadFixture(trainersJoinedFixture);
    const { escrow, trainerA, trainerB, resultHashA, resultHashB } = fix;

    await escrow.connect(trainerA).submitResult(0, resultHashA);
    await escrow.connect(trainerB).submitResult(0, resultHashB);

    return fix;
  }

  // ─── Deployment ──────────────────────────────────────────

  describe("Deployment", function () {
    it("should set correct token and slash rate", async function () {
      const { token, escrow } = await loadFixture(deployFixture);
      expect(await escrow.token()).to.equal(await token.getAddress());
      expect(await escrow.slashRate()).to.equal(5000); // 50%
    });

    it("should start with nextTaskId = 0", async function () {
      const { escrow } = await loadFixture(deployFixture);
      expect(await escrow.nextTaskId()).to.equal(0);
    });

    it("should revert if token is zero address", async function () {
      const TrainingEscrow = await ethers.getContractFactory("TrainingEscrow");
      await expect(
        TrainingEscrow.deploy(ethers.ZeroAddress, 5000)
      ).to.be.revertedWith("Invalid token address");
    });

    it("should revert if slash rate > 100%", async function () {
      const { token } = await loadFixture(deployFixture);
      const TrainingEscrow = await ethers.getContractFactory("TrainingEscrow");
      await expect(
        TrainingEscrow.deploy(await token.getAddress(), 10001)
      ).to.be.revertedWith("Slash rate exceeds 100%");
    });
  });

  // ─── Role: Task Creator ─────────────────────────────────

  describe("Role: Task Creator", function () {
    it("should create a task with correct parameters", async function () {
      const { escrow, taskCreator, modelHash, taskId, reward, minStake } =
        await loadFixture(taskCreatedFixture);

      const task = await escrow.getTaskDetails(taskId);
      expect(task.creator).to.equal(taskCreator.address);
      expect(task.modelHash).to.equal(modelHash);
      expect(task.rewardAmount).to.equal(reward);
      expect(task.minStake).to.equal(minStake);
      expect(task.maxTrainers).to.equal(5);
      expect(task.status).to.equal(0); // Open
      expect(task.trainerCount).to.equal(0);
    });

    it("should emit TaskCreated event", async function () {
      const { token, escrow, taskCreator, modelHash } =
        await loadFixture(deployFixture);

      const reward = ethers.parseEther("500");
      const minStake = ethers.parseEther("50");
      await token.connect(taskCreator).approve(await escrow.getAddress(), reward);

      await expect(
        escrow.connect(taskCreator).createTask(modelHash, reward, minStake, 3, 3600)
      )
        .to.emit(escrow, "TaskCreated");
    });

    it("should transfer reward to escrow contract", async function () {
      const { token, escrow } = await loadFixture(taskCreatedFixture);
      const balance = await token.balanceOf(await escrow.getAddress());
      expect(balance).to.equal(ethers.parseEther("1000"));
    });

    it("should revert createTask with zero reward", async function () {
      const { escrow, taskCreator, modelHash } =
        await loadFixture(deployFixture);

      await expect(
        escrow.connect(taskCreator).createTask(modelHash, 0, 100, 5, 3600)
      ).to.be.revertedWith("Reward must be > 0");
    });

    it("should revert createTask with duration < 5 minutes", async function () {
      const { token, escrow, taskCreator, modelHash } =
        await loadFixture(deployFixture);

      const reward = ethers.parseEther("100");
      await token.connect(taskCreator).approve(await escrow.getAddress(), reward);

      await expect(
        escrow.connect(taskCreator).createTask(modelHash, reward, ethers.parseEther("10"), 5, 60)
      ).to.be.revertedWith("Duration must be >= 5 minutes");
    });

    it("should increment nextTaskId", async function () {
      const { escrow } = await loadFixture(taskCreatedFixture);
      expect(await escrow.nextTaskId()).to.equal(1);
    });

    // ── Cancel Task ──────────────────────────────────────

    it("should cancel open task and refund creator", async function () {
      const { token, escrow, taskCreator, reward, taskId } =
        await loadFixture(taskCreatedFixture);

      const balBefore = await token.balanceOf(taskCreator.address);

      await expect(escrow.connect(taskCreator).cancelTask(taskId))
        .to.emit(escrow, "TaskCancelled")
        .withArgs(taskId, reward);

      const balAfter = await token.balanceOf(taskCreator.address);
      expect(balAfter - balBefore).to.equal(reward);

      const task = await escrow.getTaskDetails(taskId);
      expect(task.status).to.equal(3); // Cancelled
    });

    it("should cancel task and refund all trainer stakes", async function () {
      const { token, escrow, taskCreator, trainerA, trainerB, stakeAmount, taskId } =
        await loadFixture(trainersJoinedFixture);

      const balABefore = await token.balanceOf(trainerA.address);
      const balBBefore = await token.balanceOf(trainerB.address);

      await escrow.connect(taskCreator).cancelTask(taskId);

      const balAAfter = await token.balanceOf(trainerA.address);
      const balBAfter = await token.balanceOf(trainerB.address);

      // Trainers get full stake back
      expect(balAAfter - balABefore).to.equal(stakeAmount);
      expect(balBAfter - balBBefore).to.equal(stakeAmount);
    });

    it("should revert cancel on completed task", async function () {
      const { escrow, owner, taskCreator, trainerA, resultHashA, taskId } =
        await loadFixture(resultsSubmittedFixture);

      // Validate and complete
      await escrow.connect(owner).validateTrainer(taskId, trainerA.address, true);
      await escrow.connect(owner).completeTask(taskId);

      await expect(
        escrow.connect(taskCreator).cancelTask(taskId)
      ).to.be.revertedWith("Task already finalized");
    });
  });

  // ─── Role: Trainer ──────────────────────────────────────

  describe("Role: Trainer", function () {
    // ── Join Task ────────────────────────────────────────

    it("should join task by staking tokens", async function () {
      const { token, escrow, trainerA, minStake, taskId } =
        await loadFixture(taskCreatedFixture);

      const stakeAmount = ethers.parseEther("200");
      await token.connect(trainerA).approve(await escrow.getAddress(), stakeAmount);

      await expect(escrow.connect(trainerA).joinTask(taskId, stakeAmount))
        .to.emit(escrow, "TrainerJoined")
        .withArgs(taskId, trainerA.address, stakeAmount);
    });

    it("should move task to InProgress when first trainer joins", async function () {
      const { escrow, taskId } = await loadFixture(trainersJoinedFixture);
      const task = await escrow.getTaskDetails(taskId);
      expect(task.status).to.equal(1); // InProgress
    });

    it("should track trainer count", async function () {
      const { escrow, taskId } = await loadFixture(trainersJoinedFixture);
      const task = await escrow.getTaskDetails(taskId);
      expect(task.trainerCount).to.equal(2);
    });

    it("should revert join with stake below minimum", async function () {
      const { token, escrow, trainerC, taskId } =
        await loadFixture(taskCreatedFixture);

      const lowStake = ethers.parseEther("50"); // min is 100
      await token.connect(trainerC).approve(await escrow.getAddress(), lowStake);

      await expect(
        escrow.connect(trainerC).joinTask(taskId, lowStake)
      ).to.be.revertedWith("Stake below minimum");
    });

    it("should revert double join", async function () {
      const { token, escrow, trainerA, taskId, stakeAmount } =
        await loadFixture(trainersJoinedFixture);

      await token.connect(trainerA).approve(await escrow.getAddress(), stakeAmount);

      await expect(
        escrow.connect(trainerA).joinTask(taskId, stakeAmount)
      ).to.be.revertedWith("Already joined");
    });

    it("should revert join after deadline", async function () {
      const { token, escrow, trainerC, taskId } =
        await loadFixture(taskCreatedFixture);

      // Fast forward past deadline
      await time.increase(86401);

      const stake = ethers.parseEther("200");
      await token.connect(trainerC).approve(await escrow.getAddress(), stake);

      await expect(
        escrow.connect(trainerC).joinTask(taskId, stake)
      ).to.be.revertedWith("Task expired");
    });

    it("should enforce max trainers", async function () {
      const { token, escrow, taskCreator, modelHash } =
        await loadFixture(deployFixture);

      // Create task with maxTrainers = 2
      const reward = ethers.parseEther("100");
      const minStake = ethers.parseEther("10");
      await token.connect(taskCreator).approve(await escrow.getAddress(), reward);
      await escrow.connect(taskCreator).createTask(modelHash, reward, minStake, 2, 86400);

      const signers = await ethers.getSigners();
      const stake = ethers.parseEther("20");

      // First 2 join successfully (need tokens — mint via unused categories)
      await token.mintCategory(4, signers[6].address, ethers.parseEther("1000")); // IDO
      await token.mintCategory(5, signers[7].address, ethers.parseEther("1000")); // DaoTreasury
      await token.mintCategory(6, signers[8].address, ethers.parseEther("1000")); // InitialLiquidity

      await token.connect(signers[6]).approve(await escrow.getAddress(), stake);
      await escrow.connect(signers[6]).joinTask(0, stake);

      await token.connect(signers[7]).approve(await escrow.getAddress(), stake);
      await escrow.connect(signers[7]).joinTask(0, stake);

      // Third should fail
      await token.connect(signers[8]).approve(await escrow.getAddress(), stake);
      await expect(
        escrow.connect(signers[8]).joinTask(0, stake)
      ).to.be.revertedWith("Task is full");
    });

    // ── Submit Result ────────────────────────────────────

    it("should submit training result", async function () {
      const { escrow, trainerA, resultHashA, taskId } =
        await loadFixture(trainersJoinedFixture);

      await expect(escrow.connect(trainerA).submitResult(taskId, resultHashA))
        .to.emit(escrow, "ResultSubmitted")
        .withArgs(taskId, trainerA.address, resultHashA);
    });

    it("should revert double submission", async function () {
      const { escrow, trainerA, resultHashA, taskId } =
        await loadFixture(trainersJoinedFixture);

      await escrow.connect(trainerA).submitResult(taskId, resultHashA);

      await expect(
        escrow.connect(trainerA).submitResult(taskId, resultHashA)
      ).to.be.revertedWith("Already submitted");
    });

    it("should revert submission by non-participant", async function () {
      const { escrow, outsider, taskId } =
        await loadFixture(trainersJoinedFixture);

      const hash = ethers.keccak256(ethers.toUtf8Bytes("fake"));

      await expect(
        escrow.connect(outsider).submitResult(taskId, hash)
      ).to.be.revertedWith("Not a participant");
    });

    it("should revert submission with zero hash", async function () {
      const { escrow, trainerA, taskId } =
        await loadFixture(trainersJoinedFixture);

      await expect(
        escrow.connect(trainerA).submitResult(taskId, ethers.ZeroHash)
      ).to.be.revertedWith("Invalid result hash");
    });

    it("should revert submission after deadline", async function () {
      const { escrow, trainerA, resultHashA, taskId } =
        await loadFixture(trainersJoinedFixture);

      await time.increase(86401);

      await expect(
        escrow.connect(trainerA).submitResult(taskId, resultHashA)
      ).to.be.revertedWith("Task expired");
    });

    // ── Claim Reward ─────────────────────────────────────

    it("should claim reward + stake after validation", async function () {
      const { token, escrow, owner, trainerA, trainerB, stakeAmount, reward, taskId } =
        await loadFixture(resultsSubmittedFixture);

      // Validate both trainers
      await escrow.connect(owner).validateTrainer(taskId, trainerA.address, true);
      await escrow.connect(owner).validateTrainer(taskId, trainerB.address, true);
      await escrow.connect(owner).completeTask(taskId);

      // Trainer A claims
      const balBefore = await token.balanceOf(trainerA.address);
      await expect(escrow.connect(trainerA).claimReward(taskId))
        .to.emit(escrow, "RewardDistributed");

      const balAfter = await token.balanceOf(trainerA.address);

      // 2 validated trainers → reward = 1000 / 2 = 500 MDT each
      // Plus stake return = 200 MDT
      const expectedPayout = ethers.parseEther("500") + stakeAmount;
      expect(balAfter - balBefore).to.equal(expectedPayout);
    });

    it("should revert claim if not validated", async function () {
      const { escrow, owner, trainerA, trainerB, taskId } =
        await loadFixture(resultsSubmittedFixture);

      // Only validate B
      await escrow.connect(owner).validateTrainer(taskId, trainerB.address, true);
      await escrow.connect(owner).completeTask(taskId);

      await expect(
        escrow.connect(trainerA).claimReward(taskId)
      ).to.be.revertedWith("Not validated");
    });

    it("should revert double claim", async function () {
      const { escrow, owner, trainerA, trainerB, taskId } =
        await loadFixture(resultsSubmittedFixture);

      await escrow.connect(owner).validateTrainer(taskId, trainerA.address, true);
      await escrow.connect(owner).validateTrainer(taskId, trainerB.address, true);
      await escrow.connect(owner).completeTask(taskId);

      await escrow.connect(trainerA).claimReward(taskId);

      await expect(
        escrow.connect(trainerA).claimReward(taskId)
      ).to.be.revertedWith("Already claimed");
    });

    it("should revert claim on incomplete task", async function () {
      const { escrow, trainerA, taskId } =
        await loadFixture(resultsSubmittedFixture);

      await expect(
        escrow.connect(trainerA).claimReward(taskId)
      ).to.be.revertedWith("Task not completed");
    });
  });

  // ─── Role: Owner / Verifier ─────────────────────────────

  describe("Role: Owner (Verifier)", function () {
    // ── Validate Trainer ─────────────────────────────────

    it("should validate trainer as valid", async function () {
      const { escrow, owner, trainerA, taskId } =
        await loadFixture(resultsSubmittedFixture);

      await expect(
        escrow.connect(owner).validateTrainer(taskId, trainerA.address, true)
      )
        .to.emit(escrow, "TrainerValidated")
        .withArgs(taskId, trainerA.address, true);

      const trainer = await escrow.trainers(taskId, trainerA.address);
      expect(trainer.validated).to.equal(true);
      expect(trainer.slashed).to.equal(false);
    });

    it("should slash invalid trainer at 50%", async function () {
      const { token, escrow, owner, trainerA, stakeAmount, taskId } =
        await loadFixture(resultsSubmittedFixture);

      const balBefore = await token.balanceOf(trainerA.address);

      await expect(
        escrow.connect(owner).validateTrainer(taskId, trainerA.address, false)
      )
        .to.emit(escrow, "TrainerSlashed")
        .withArgs(taskId, trainerA.address, stakeAmount / 2n);

      const balAfter = await token.balanceOf(trainerA.address);

      // Should get back 50% of stake (200 * 50% = 100)
      expect(balAfter - balBefore).to.equal(stakeAmount / 2n);

      // Total slashed should be updated
      expect(await escrow.totalSlashed()).to.equal(stakeAmount / 2n);

      const trainer = await escrow.trainers(taskId, trainerA.address);
      expect(trainer.slashed).to.equal(true);
    });

    it("should revert validate by non-owner", async function () {
      const { escrow, trainerA, trainerB, taskId } =
        await loadFixture(resultsSubmittedFixture);

      await expect(
        escrow.connect(trainerA).validateTrainer(taskId, trainerB.address, true)
      ).to.be.reverted; // OwnableUnauthorizedAccount
    });

    it("should revert validate without submission", async function () {
      const { escrow, owner, trainerC, taskId } =
        await loadFixture(trainersJoinedFixture);

      // trainerC hasn't joined, let alone submitted
      await expect(
        escrow.connect(owner).validateTrainer(taskId, trainerC.address, true)
      ).to.be.revertedWith("Not a participant");
    });

    it("should revert re-validate already processed trainer", async function () {
      const { escrow, owner, trainerA, taskId } =
        await loadFixture(resultsSubmittedFixture);

      await escrow.connect(owner).validateTrainer(taskId, trainerA.address, true);

      await expect(
        escrow.connect(owner).validateTrainer(taskId, trainerA.address, true)
      ).to.be.revertedWith("Already processed");
    });

    // ── Complete Task ────────────────────────────────────

    it("should complete task", async function () {
      const { escrow, owner, trainerA, taskId } =
        await loadFixture(resultsSubmittedFixture);

      await escrow.connect(owner).validateTrainer(taskId, trainerA.address, true);

      await expect(escrow.connect(owner).completeTask(taskId))
        .to.emit(escrow, "TaskCompleted")
        .withArgs(taskId);

      const task = await escrow.getTaskDetails(taskId);
      expect(task.status).to.equal(2); // Completed
    });

    it("should revert complete by non-owner", async function () {
      const { escrow, taskCreator, taskId } =
        await loadFixture(resultsSubmittedFixture);

      await expect(
        escrow.connect(taskCreator).completeTask(taskId)
      ).to.be.reverted; // OwnableUnauthorizedAccount
    });

    // ── Slash Rate Admin ─────────────────────────────────

    it("should update slash rate", async function () {
      const { escrow, owner } = await loadFixture(deployFixture);

      await escrow.connect(owner).setSlashRate(7500); // 75%
      expect(await escrow.slashRate()).to.equal(7500);
    });

    it("should revert set slash rate > 100%", async function () {
      const { escrow, owner } = await loadFixture(deployFixture);

      await expect(
        escrow.connect(owner).setSlashRate(10001)
      ).to.be.revertedWith("Rate exceeds 100%");
    });

    it("should revert set slash rate by non-owner", async function () {
      const { escrow, outsider } = await loadFixture(deployFixture);

      await expect(
        escrow.connect(outsider).setSlashRate(1000)
      ).to.be.reverted;
    });

    // ── Withdraw Slashed ─────────────────────────────────

    it("should withdraw slashed tokens to treasury", async function () {
      const { token, escrow, owner, trainerA, stakeAmount, taskId } =
        await loadFixture(resultsSubmittedFixture);

      // Slash trainer A
      await escrow.connect(owner).validateTrainer(taskId, trainerA.address, false);

      const treasuryAddr = owner.address;
      const balBefore = await token.balanceOf(treasuryAddr);

      await escrow.connect(owner).withdrawSlashed(treasuryAddr);

      const balAfter = await token.balanceOf(treasuryAddr);
      expect(balAfter - balBefore).to.equal(stakeAmount / 2n);

      // totalSlashed should be reset
      expect(await escrow.totalSlashed()).to.equal(0);
    });

    it("should revert withdraw with zero slashed", async function () {
      const { escrow, owner } = await loadFixture(deployFixture);

      await expect(
        escrow.connect(owner).withdrawSlashed(owner.address)
      ).to.be.revertedWith("No slashed funds");
    });

    it("should revert withdraw by non-owner", async function () {
      const { escrow, outsider } = await loadFixture(resultsSubmittedFixture);

      await expect(
        escrow.connect(outsider).withdrawSlashed(outsider.address)
      ).to.be.reverted;
    });

    // ── Owner Cancel After Deadline ──────────────────────

    it("should allow owner to cancel after deadline", async function () {
      const { escrow, owner, taskId } = await loadFixture(trainersJoinedFixture);

      await time.increase(86401); // Past deadline

      await expect(escrow.connect(owner).cancelTask(taskId))
        .to.emit(escrow, "TaskCancelled");

      const task = await escrow.getTaskDetails(taskId);
      expect(task.status).to.equal(3); // Cancelled
    });

    it("should revert owner cancel before deadline (non-creator)", async function () {
      const { escrow, owner, taskId } = await loadFixture(trainersJoinedFixture);

      await expect(
        escrow.connect(owner).cancelTask(taskId)
      ).to.be.revertedWith("Not authorized");
    });
  });

  // ─── Role: Outsider ─────────────────────────────────────

  describe("Role: Outsider (unauthorized)", function () {
    it("should revert submit by outsider", async function () {
      const { escrow, outsider, taskId } =
        await loadFixture(trainersJoinedFixture);

      const hash = ethers.keccak256(ethers.toUtf8Bytes("fake"));
      await expect(
        escrow.connect(outsider).submitResult(taskId, hash)
      ).to.be.revertedWith("Not a participant");
    });

    it("should revert claim by outsider", async function () {
      const { escrow, owner, trainerA, trainerB, outsider, taskId } =
        await loadFixture(resultsSubmittedFixture);

      await escrow.connect(owner).validateTrainer(taskId, trainerA.address, true);
      await escrow.connect(owner).validateTrainer(taskId, trainerB.address, true);
      await escrow.connect(owner).completeTask(taskId);

      await expect(
        escrow.connect(outsider).claimReward(taskId)
      ).to.be.revertedWith("Not validated");
    });

    it("should revert cancel by outsider", async function () {
      const { escrow, outsider, taskId } =
        await loadFixture(taskCreatedFixture);

      await expect(
        escrow.connect(outsider).cancelTask(taskId)
      ).to.be.revertedWith("Not authorized");
    });
  });

  // ─── Full Workflow E2E ──────────────────────────────────

  describe("Full Workflow (E2E)", function () {
    it("should handle the complete lifecycle: create → join → submit → validate → complete → claim", async function () {
      const {
        token, escrow, owner, taskCreator,
        trainerA, trainerB, trainerC,
        modelHash, resultHashA, resultHashB, resultHashC,
      } = await loadFixture(deployFixture);

      // 1. Creator creates task
      const reward = ethers.parseEther("600");
      const minStake = ethers.parseEther("50");
      await token.connect(taskCreator).approve(await escrow.getAddress(), reward);
      await escrow.connect(taskCreator).createTask(modelHash, reward, minStake, 3, 86400);

      // Verify task created
      let task = await escrow.getTaskDetails(0);
      expect(task.status).to.equal(0); // Open

      // 2. Three trainers join
      const stake = ethers.parseEther("100");
      for (const trainer of [trainerA, trainerB, trainerC]) {
        await token.connect(trainer).approve(await escrow.getAddress(), stake);
        await escrow.connect(trainer).joinTask(0, stake);
      }

      task = await escrow.getTaskDetails(0);
      expect(task.status).to.equal(1); // InProgress
      expect(task.trainerCount).to.equal(3);

      // Verify trainer list
      const trainerList = await escrow.getTaskTrainers(0);
      expect(trainerList.length).to.equal(3);

      // 3. All trainers submit results
      await escrow.connect(trainerA).submitResult(0, resultHashA);
      await escrow.connect(trainerB).submitResult(0, resultHashB);
      await escrow.connect(trainerC).submitResult(0, resultHashC);

      // 4. Owner validates: A valid, B valid, C invalid (slashed)
      await escrow.connect(owner).validateTrainer(0, trainerA.address, true);
      await escrow.connect(owner).validateTrainer(0, trainerB.address, true);

      const cBalBefore = await token.balanceOf(trainerC.address);
      await escrow.connect(owner).validateTrainer(0, trainerC.address, false);
      const cBalAfter = await token.balanceOf(trainerC.address);
      // C gets 50% of 100 = 50 back
      expect(cBalAfter - cBalBefore).to.equal(ethers.parseEther("50"));

      // 5. Owner completes task
      await escrow.connect(owner).completeTask(0);

      // 6. Valid trainers claim rewards
      // 2 valid trainers: each gets 600/2 = 300 reward + 100 stake back
      const aBalBefore = await token.balanceOf(trainerA.address);
      await escrow.connect(trainerA).claimReward(0);
      const aBalAfter = await token.balanceOf(trainerA.address);
      expect(aBalAfter - aBalBefore).to.equal(ethers.parseEther("400")); // 300 + 100

      const bBalBefore = await token.balanceOf(trainerB.address);
      await escrow.connect(trainerB).claimReward(0);
      const bBalAfter = await token.balanceOf(trainerB.address);
      expect(bBalAfter - bBalBefore).to.equal(ethers.parseEther("400")); // 300 + 100

      // C cannot claim (slashed)
      await expect(
        escrow.connect(trainerC).claimReward(0)
      ).to.be.revertedWith("Not validated");

      // 7. Owner withdraws slashed funds
      const slashed = await escrow.totalSlashed();
      expect(slashed).to.equal(ethers.parseEther("50"));

      await escrow.connect(owner).withdrawSlashed(owner.address);
      expect(await escrow.totalSlashed()).to.equal(0);
    });
  });
});
