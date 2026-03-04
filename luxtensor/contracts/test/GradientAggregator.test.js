// SPDX-License-Identifier: MIT
/**
 * GradientAggregator — Full Role-Based Tests
 *
 * Roles tested:
 *   - Owner/Deployer: deploys contract
 *   - Job Creator: creates jobs, finalizes rounds, cancels jobs
 *   - Participant A/B/C: submit gradients, claim rewards
 *   - Non-participant: tries unauthorized actions (should revert)
 */

const { expect } = require("chai");
const { ethers } = require("hardhat");
const { loadFixture } = require("@nomicfoundation/hardhat-network-helpers");

describe("GradientAggregator", function () {
  // ─── Fixtures ────────────────────────────────────────────

  async function deployFixture() {
    const [owner, creator, participantA, participantB, participantC, outsider] =
      await ethers.getSigners();

    // Deploy MDTToken
    const MDTToken = await ethers.getContractFactory("MDTToken");
    const token = await MDTToken.deploy();
    await token.waitForDeployment();

    // Mint tokens to creator and participants via mintCategory (category 0 = EmissionRewards)
    const mintAmount = ethers.parseEther("100000");
    await token.mintCategory(0, creator.address, mintAmount);
    await token.mintCategory(1, participantA.address, ethers.parseEther("10000"));
    await token.mintCategory(2, participantB.address, ethers.parseEther("10000"));

    // Deploy GradientAggregator
    const GradientAggregator = await ethers.getContractFactory("GradientAggregator");
    const aggregator = await GradientAggregator.deploy(await token.getAddress());
    await aggregator.waitForDeployment();

    // Common test values
    const modelHash = ethers.keccak256(ethers.toUtf8Bytes("resnet50-v1"));
    const gradientHashA = ethers.keccak256(ethers.toUtf8Bytes("gradient-A"));
    const gradientHashB = ethers.keccak256(ethers.toUtf8Bytes("gradient-B"));
    const gradientHashC = ethers.keccak256(ethers.toUtf8Bytes("gradient-C"));
    const aggregatedHash = ethers.keccak256(ethers.toUtf8Bytes("fedavg-round1"));

    return {
      token, aggregator,
      owner, creator, participantA, participantB, participantC, outsider,
      modelHash, gradientHashA, gradientHashB, gradientHashC, aggregatedHash,
    };
  }

  async function jobCreatedFixture() {
    const fix = await loadFixture(deployFixture);
    const { token, aggregator, creator, modelHash } = fix;

    // Creator approves and creates job
    const reward = ethers.parseEther("1000");
    await token.connect(creator).approve(await aggregator.getAddress(), reward);
    await aggregator.connect(creator).createJob(
      modelHash,
      3,           // 3 rounds
      reward,
      5,           // max 5 participants
      3600         // 1 hour per round
    );

    return { ...fix, reward, jobId: 0 };
  }

  // ─── Deployment ──────────────────────────────────────────

  describe("Deployment", function () {
    it("should set the correct token address", async function () {
      const { token, aggregator } = await loadFixture(deployFixture);
      expect(await aggregator.token()).to.equal(await token.getAddress());
    });

    it("should start with nextJobId = 0", async function () {
      const { aggregator } = await loadFixture(deployFixture);
      expect(await aggregator.nextJobId()).to.equal(0);
    });

    it("should revert if token address is zero", async function () {
      const GradientAggregator = await ethers.getContractFactory("GradientAggregator");
      await expect(
        GradientAggregator.deploy(ethers.ZeroAddress)
      ).to.be.revertedWith("Invalid token address");
    });
  });

  // ─── Role: Job Creator ──────────────────────────────────

  describe("Role: Job Creator", function () {
    it("should create a job with correct parameters", async function () {
      const { aggregator, creator, modelHash, jobId } =
        await loadFixture(jobCreatedFixture);

      const job = await aggregator.getJobDetails(jobId);
      expect(job.modelHash).to.equal(modelHash);
      expect(job.totalRounds).to.equal(3);
      expect(job.currentRound).to.equal(1);
      expect(job.rewardPool).to.equal(ethers.parseEther("1000"));
      expect(job.maxParticipants).to.equal(5);
      expect(job.status).to.equal(0); // Active
      expect(job.creator).to.equal(creator.address);
    });

    it("should emit JobCreated event", async function () {
      const { token, aggregator, creator, modelHash } =
        await loadFixture(deployFixture);

      const reward = ethers.parseEther("500");
      await token.connect(creator).approve(await aggregator.getAddress(), reward);

      await expect(
        aggregator.connect(creator).createJob(modelHash, 2, reward, 10, 120)
      )
        .to.emit(aggregator, "JobCreated")
        .withArgs(0, modelHash, 2, reward, 10);
    });

    it("should transfer reward tokens to contract", async function () {
      const { token, aggregator, creator } =
        await loadFixture(jobCreatedFixture);

      const balance = await token.balanceOf(await aggregator.getAddress());
      expect(balance).to.equal(ethers.parseEther("1000"));
    });

    it("should revert createJob with zero rounds", async function () {
      const { token, aggregator, creator, modelHash } =
        await loadFixture(deployFixture);

      const reward = ethers.parseEther("100");
      await token.connect(creator).approve(await aggregator.getAddress(), reward);

      await expect(
        aggregator.connect(creator).createJob(modelHash, 0, reward, 5, 3600)
      ).to.be.revertedWith("Rounds must be > 0");
    });

    it("should revert createJob with zero reward", async function () {
      const { aggregator, creator, modelHash } =
        await loadFixture(deployFixture);

      await expect(
        aggregator.connect(creator).createJob(modelHash, 3, 0, 5, 3600)
      ).to.be.revertedWith("Reward must be > 0");
    });

    it("should revert createJob with deadline < 60s", async function () {
      const { token, aggregator, creator, modelHash } =
        await loadFixture(deployFixture);

      const reward = ethers.parseEther("100");
      await token.connect(creator).approve(await aggregator.getAddress(), reward);

      await expect(
        aggregator.connect(creator).createJob(modelHash, 3, reward, 5, 30)
      ).to.be.revertedWith("Deadline must be >= 60s");
    });

    it("should increment nextJobId after creation", async function () {
      const { aggregator } = await loadFixture(jobCreatedFixture);
      expect(await aggregator.nextJobId()).to.equal(1);
    });

    // ── Finalize Round ────────────────────────────────────

    it("should finalize a round with valid participants", async function () {
      const {
        aggregator, creator, participantA, participantB,
        gradientHashA, gradientHashB, aggregatedHash, jobId,
      } = await loadFixture(jobCreatedFixture);

      // Participants submit gradients
      await aggregator.connect(participantA).submitGradient(jobId, gradientHashA, 1000);
      await aggregator.connect(participantB).submitGradient(jobId, gradientHashB, 2000);

      // Creator finalizes round 1
      await expect(
        aggregator.connect(creator).finalizeRound(
          jobId, aggregatedHash, [participantA.address, participantB.address]
        )
      )
        .to.emit(aggregator, "RoundFinalized")
        .withArgs(jobId, 1, aggregatedHash, 2, 3000);

      // Job should advance to round 2
      const job = await aggregator.getJobDetails(jobId);
      expect(job.currentRound).to.equal(2);
    });

    it("should complete job after all rounds finalized", async function () {
      const {
        aggregator, creator, participantA,
        gradientHashA, jobId,
      } = await loadFixture(jobCreatedFixture);

      // Run all 3 rounds
      for (let round = 1; round <= 3; round++) {
        const gradHash = ethers.keccak256(ethers.toUtf8Bytes(`gradient-round-${round}`));
        const aggHash = ethers.keccak256(ethers.toUtf8Bytes(`agg-round-${round}`));

        await aggregator.connect(participantA).submitGradient(jobId, gradHash, 500);
        await aggregator.connect(creator).finalizeRound(
          jobId, aggHash, [participantA.address]
        );
      }

      const job = await aggregator.getJobDetails(jobId);
      expect(job.status).to.equal(1); // Completed
    });

    it("should emit JobCompleted after final round", async function () {
      const {
        aggregator, creator, participantA, jobId,
      } = await loadFixture(jobCreatedFixture);

      for (let round = 1; round <= 3; round++) {
        const gradHash = ethers.keccak256(ethers.toUtf8Bytes(`g-${round}`));
        const aggHash = ethers.keccak256(ethers.toUtf8Bytes(`a-${round}`));
        await aggregator.connect(participantA).submitGradient(jobId, gradHash, 100);

        if (round === 3) {
          await expect(
            aggregator.connect(creator).finalizeRound(jobId, aggHash, [participantA.address])
          ).to.emit(aggregator, "JobCompleted").withArgs(jobId, 3);
        } else {
          await aggregator.connect(creator).finalizeRound(jobId, aggHash, [participantA.address]);
        }
      }
    });

    it("should revert finalize by non-creator", async function () {
      const {
        aggregator, participantA, gradientHashA, aggregatedHash, jobId,
      } = await loadFixture(jobCreatedFixture);

      await aggregator.connect(participantA).submitGradient(jobId, gradientHashA, 100);

      await expect(
        aggregator.connect(participantA).finalizeRound(
          jobId, aggregatedHash, [participantA.address]
        )
      ).to.be.revertedWith("Only creator can finalize");
    });

    it("should revert finalize with no submissions", async function () {
      const { aggregator, creator, participantA, aggregatedHash, jobId } =
        await loadFixture(jobCreatedFixture);

      await expect(
        aggregator.connect(creator).finalizeRound(
          jobId, aggregatedHash, [participantA.address]
        )
      ).to.be.revertedWith("No submissions this round");
    });

    // ── Cancel Job ────────────────────────────────────────

    it("should cancel job and refund reward", async function () {
      const { token, aggregator, creator, jobId } =
        await loadFixture(jobCreatedFixture);

      const balBefore = await token.balanceOf(creator.address);

      await expect(aggregator.connect(creator).cancelJob(jobId))
        .to.emit(aggregator, "JobCancelled")
        .withArgs(jobId, ethers.parseEther("1000"));

      const balAfter = await token.balanceOf(creator.address);
      expect(balAfter - balBefore).to.equal(ethers.parseEther("1000"));

      const job = await aggregator.getJobDetails(jobId);
      expect(job.status).to.equal(2); // Cancelled
    });

    it("should revert cancel by non-creator", async function () {
      const { aggregator, outsider, jobId } =
        await loadFixture(jobCreatedFixture);

      await expect(
        aggregator.connect(outsider).cancelJob(jobId)
      ).to.be.revertedWith("Only creator can cancel");
    });
  });

  // ─── Role: Participant ──────────────────────────────────

  describe("Role: Participant", function () {
    it("should submit gradient for current round", async function () {
      const { aggregator, participantA, gradientHashA, jobId } =
        await loadFixture(jobCreatedFixture);

      await expect(
        aggregator.connect(participantA).submitGradient(jobId, gradientHashA, 1000)
      )
        .to.emit(aggregator, "GradientSubmitted")
        .withArgs(jobId, 1, participantA.address, gradientHashA, 1000);
    });

    it("should store submission data correctly", async function () {
      const { aggregator, participantA, gradientHashA, jobId } =
        await loadFixture(jobCreatedFixture);

      await aggregator.connect(participantA).submitGradient(jobId, gradientHashA, 2500);

      const sub = await aggregator.getSubmission(jobId, 1, participantA.address);
      expect(sub.gradientHash).to.equal(gradientHashA);
      expect(sub.dataSize).to.equal(2500);
      expect(sub.validated).to.equal(false);
    });

    it("should revert double submission in same round", async function () {
      const { aggregator, participantA, gradientHashA, jobId } =
        await loadFixture(jobCreatedFixture);

      await aggregator.connect(participantA).submitGradient(jobId, gradientHashA, 100);

      await expect(
        aggregator.connect(participantA).submitGradient(jobId, gradientHashA, 200)
      ).to.be.revertedWith("Already submitted this round");
    });

    it("should revert submission with zero data size", async function () {
      const { aggregator, participantA, gradientHashA, jobId } =
        await loadFixture(jobCreatedFixture);

      await expect(
        aggregator.connect(participantA).submitGradient(jobId, gradientHashA, 0)
      ).to.be.revertedWith("Data size must be > 0");
    });

    it("should revert submission with zero gradient hash", async function () {
      const { aggregator, participantA, jobId } =
        await loadFixture(jobCreatedFixture);

      await expect(
        aggregator.connect(participantA).submitGradient(
          jobId, ethers.ZeroHash, 100
        )
      ).to.be.revertedWith("Invalid gradient hash");
    });

    it("should track round participants correctly", async function () {
      const { aggregator, participantA, participantB, gradientHashA, gradientHashB, jobId } =
        await loadFixture(jobCreatedFixture);

      await aggregator.connect(participantA).submitGradient(jobId, gradientHashA, 100);
      await aggregator.connect(participantB).submitGradient(jobId, gradientHashB, 200);

      const participants = await aggregator.getRoundParticipants(jobId, 1);
      expect(participants.length).to.equal(2);
      expect(participants).to.include(participantA.address);
      expect(participants).to.include(participantB.address);
    });

    it("should revert submission to cancelled job", async function () {
      const { aggregator, creator, participantA, gradientHashA, jobId } =
        await loadFixture(jobCreatedFixture);

      await aggregator.connect(creator).cancelJob(jobId);

      await expect(
        aggregator.connect(participantA).submitGradient(jobId, gradientHashA, 100)
      ).to.be.revertedWith("Job not active");
    });

    // ── Claim Reward ──────────────────────────────────────

    it("should claim proportional reward after job completes", async function () {
      const { token, aggregator, creator, participantA, participantB, jobId } =
        await loadFixture(jobCreatedFixture);

      // Both participate in all 3 rounds
      for (let r = 1; r <= 3; r++) {
        const ghA = ethers.keccak256(ethers.toUtf8Bytes(`gA-${r}`));
        const ghB = ethers.keccak256(ethers.toUtf8Bytes(`gB-${r}`));
        const agg = ethers.keccak256(ethers.toUtf8Bytes(`agg-${r}`));

        await aggregator.connect(participantA).submitGradient(jobId, ghA, 100);
        await aggregator.connect(participantB).submitGradient(jobId, ghB, 100);
        await aggregator.connect(creator).finalizeRound(
          jobId, agg, [participantA.address, participantB.address]
        );
      }

      // Each has 3 validated rounds, total 6 participant-rounds
      // Each should get: 1000 * 3 / 6 = 500 MDT
      const balBefore = await token.balanceOf(participantA.address);
      await aggregator.connect(participantA).claimReward(jobId);
      const balAfter = await token.balanceOf(participantA.address);

      expect(balAfter - balBefore).to.equal(ethers.parseEther("500"));
    });

    it("should emit RewardClaimed event", async function () {
      const { aggregator, creator, participantA, jobId } =
        await loadFixture(jobCreatedFixture);

      for (let r = 1; r <= 3; r++) {
        const gh = ethers.keccak256(ethers.toUtf8Bytes(`g-${r}`));
        const agg = ethers.keccak256(ethers.toUtf8Bytes(`a-${r}`));
        await aggregator.connect(participantA).submitGradient(jobId, gh, 100);
        await aggregator.connect(creator).finalizeRound(jobId, agg, [participantA.address]);
      }

      await expect(aggregator.connect(participantA).claimReward(jobId))
        .to.emit(aggregator, "RewardClaimed")
        .withArgs(jobId, participantA.address, ethers.parseEther("1000"));
    });

    it("should revert double claim", async function () {
      const { aggregator, creator, participantA, jobId } =
        await loadFixture(jobCreatedFixture);

      for (let r = 1; r <= 3; r++) {
        const gh = ethers.keccak256(ethers.toUtf8Bytes(`g-${r}`));
        const agg = ethers.keccak256(ethers.toUtf8Bytes(`a-${r}`));
        await aggregator.connect(participantA).submitGradient(jobId, gh, 100);
        await aggregator.connect(creator).finalizeRound(jobId, agg, [participantA.address]);
      }

      await aggregator.connect(participantA).claimReward(jobId);

      await expect(
        aggregator.connect(participantA).claimReward(jobId)
      ).to.be.revertedWith("Already claimed");
    });

    it("should revert claim on active job", async function () {
      const { aggregator, participantA, jobId } =
        await loadFixture(jobCreatedFixture);

      await expect(
        aggregator.connect(participantA).claimReward(jobId)
      ).to.be.revertedWith("Job not completed");
    });

    it("should give more reward to participant with more validated rounds", async function () {
      const { token, aggregator, creator, participantA, participantB, jobId } =
        await loadFixture(jobCreatedFixture);

      // Round 1: both participate
      let ghA = ethers.keccak256(ethers.toUtf8Bytes("gA-1"));
      let ghB = ethers.keccak256(ethers.toUtf8Bytes("gB-1"));
      let agg = ethers.keccak256(ethers.toUtf8Bytes("a-1"));
      await aggregator.connect(participantA).submitGradient(jobId, ghA, 100);
      await aggregator.connect(participantB).submitGradient(jobId, ghB, 100);
      await aggregator.connect(creator).finalizeRound(
        jobId, agg, [participantA.address, participantB.address]
      );

      // Rounds 2-3: only A participates
      for (let r = 2; r <= 3; r++) {
        ghA = ethers.keccak256(ethers.toUtf8Bytes(`gA-${r}`));
        agg = ethers.keccak256(ethers.toUtf8Bytes(`a-${r}`));
        await aggregator.connect(participantA).submitGradient(jobId, ghA, 100);
        await aggregator.connect(creator).finalizeRound(jobId, agg, [participantA.address]);
      }

      // A: 3 rounds, B: 1 round, total: 4 participant-rounds
      // A gets: 1000 * 3 / 4 = 750 MDT
      // B gets: 1000 * 1 / 4 = 250 MDT
      const balABefore = await token.balanceOf(participantA.address);
      await aggregator.connect(participantA).claimReward(jobId);
      const balAAfter = await token.balanceOf(participantA.address);
      expect(balAAfter - balABefore).to.equal(ethers.parseEther("750"));

      const balBBefore = await token.balanceOf(participantB.address);
      await aggregator.connect(participantB).claimReward(jobId);
      const balBAfter = await token.balanceOf(participantB.address);
      expect(balBAfter - balBBefore).to.equal(ethers.parseEther("250"));
    });
  });

  // ─── Role: Outsider / Unauthorized ──────────────────────

  describe("Role: Outsider (unauthorized)", function () {
    it("should revert claim with no contributions", async function () {
      const { aggregator, creator, participantA, outsider, jobId } =
        await loadFixture(jobCreatedFixture);

      for (let r = 1; r <= 3; r++) {
        const gh = ethers.keccak256(ethers.toUtf8Bytes(`g-${r}`));
        const agg = ethers.keccak256(ethers.toUtf8Bytes(`a-${r}`));
        await aggregator.connect(participantA).submitGradient(jobId, gh, 100);
        await aggregator.connect(creator).finalizeRound(jobId, agg, [participantA.address]);
      }

      await expect(
        aggregator.connect(outsider).claimReward(jobId)
      ).to.be.revertedWith("No validated contributions");
    });

    it("should revert cancel job by outsider", async function () {
      const { aggregator, outsider, jobId } =
        await loadFixture(jobCreatedFixture);

      await expect(
        aggregator.connect(outsider).cancelJob(jobId)
      ).to.be.revertedWith("Only creator can cancel");
    });

    it("should revert finalize by outsider", async function () {
      const { aggregator, participantA, outsider, gradientHashA, aggregatedHash, jobId } =
        await loadFixture(jobCreatedFixture);

      await aggregator.connect(participantA).submitGradient(jobId, gradientHashA, 100);

      await expect(
        aggregator.connect(outsider).finalizeRound(
          jobId, aggregatedHash, [participantA.address]
        )
      ).to.be.revertedWith("Only creator can finalize");
    });
  });

  // ─── Edge Cases ─────────────────────────────────────────

  describe("Edge Cases", function () {
    it("should enforce max participants per round", async function () {
      const { token, aggregator, creator, modelHash } =
        await loadFixture(deployFixture);

      // Create job with max 2 participants
      const reward = ethers.parseEther("100");
      await token.connect(creator).approve(await aggregator.getAddress(), reward);
      await aggregator.connect(creator).createJob(modelHash, 1, reward, 2, 60);

      const signers = await ethers.getSigners();

      const gh1 = ethers.keccak256(ethers.toUtf8Bytes("g1"));
      const gh2 = ethers.keccak256(ethers.toUtf8Bytes("g2"));
      const gh3 = ethers.keccak256(ethers.toUtf8Bytes("g3"));

      await aggregator.connect(signers[4]).submitGradient(0, gh1, 100);
      await aggregator.connect(signers[5]).submitGradient(0, gh2, 100);

      await expect(
        aggregator.connect(signers[6]).submitGradient(0, gh3, 100)
      ).to.be.revertedWith("Round is full");
    });

    it("should handle multiple jobs independently", async function () {
      const { token, aggregator, creator, modelHash } =
        await loadFixture(deployFixture);

      const reward = ethers.parseEther("100");
      await token.connect(creator).approve(await aggregator.getAddress(), ethers.parseEther("200"));

      await aggregator.connect(creator).createJob(modelHash, 1, reward, 5, 60);
      await aggregator.connect(creator).createJob(modelHash, 2, reward, 3, 120);

      expect(await aggregator.nextJobId()).to.equal(2);

      const job0 = await aggregator.getJobDetails(0);
      const job1 = await aggregator.getJobDetails(1);
      expect(job0.totalRounds).to.equal(1);
      expect(job1.totalRounds).to.equal(2);
      expect(job1.maxParticipants).to.equal(3);
    });

    it("should allow participant to submit in multiple rounds", async function () {
      const { aggregator, creator, participantA, jobId } =
        await loadFixture(jobCreatedFixture);

      // Round 1
      const gh1 = ethers.keccak256(ethers.toUtf8Bytes("round1"));
      const agg1 = ethers.keccak256(ethers.toUtf8Bytes("agg1"));
      await aggregator.connect(participantA).submitGradient(jobId, gh1, 100);
      await aggregator.connect(creator).finalizeRound(jobId, agg1, [participantA.address]);

      // Round 2 — same participant, new gradient
      const gh2 = ethers.keccak256(ethers.toUtf8Bytes("round2"));
      const agg2 = ethers.keccak256(ethers.toUtf8Bytes("agg2"));
      await aggregator.connect(participantA).submitGradient(jobId, gh2, 200);
      await aggregator.connect(creator).finalizeRound(jobId, agg2, [participantA.address]);

      const myRounds = await aggregator.participantRounds(jobId, participantA.address);
      expect(myRounds).to.equal(2);
    });
  });
});
