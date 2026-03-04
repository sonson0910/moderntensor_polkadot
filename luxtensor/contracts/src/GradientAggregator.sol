// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title GradientAggregator
 * @dev On-chain federated learning coordinator on Polkadot Hub (pallet-revive EVM).
 *
 * Implements Federated Averaging (FedAvg):
 *   1. Owner creates a TrainingJob with a model hash, number of rounds, and reward.
 *   2. Registered participants submit gradient hashes each round.
 *   3. Owner (aggregator) finalizes each round with the aggregated model hash.
 *   4. After all rounds complete, participants can claim proportional rewards.
 *
 * This contract stores gradient *hashes* (not raw gradients) for gas efficiency
 * and uses Proof-of-Training attestations that can be verified off-chain or
 * combined with ZkMLVerifier for on-chain proof verification.
 */
contract GradientAggregator is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    // ──────────────────────────────────────
    // Data Structures
    // ──────────────────────────────────────

    enum JobStatus {
        Active,
        Completed,
        Cancelled
    }

    struct TrainingJob {
        bytes32 modelHash; // Initial model checkpoint hash
        uint256 totalRounds; // Number of federated rounds
        uint256 currentRound; // Current round (1-indexed when active)
        uint256 rewardPool; // Total MDT reward for the job
        uint256 maxParticipants; // Max participants per round
        uint256 roundDeadline; // Seconds allowed per round
        JobStatus status;
        address creator;
        uint256 createdAt;
    }

    struct GradientSubmission {
        bytes32 gradientHash; // Hash of the gradient update
        uint256 dataSize; // Size of training data used (samples)
        uint256 timestamp;
        bool validated; // Whether the submission passed validation
    }

    struct RoundResult {
        bytes32 aggregatedHash; // FedAvg result hash for this round
        uint256 participantCount;
        uint256 totalDataSize; // Sum of all participants' data sizes
        uint256 finalizedAt;
    }

    // ──────────────────────────────────────
    // State
    // ──────────────────────────────────────

    IERC20 public immutable token;

    uint256 public nextJobId;

    mapping(uint256 => TrainingJob) public jobs;

    // jobId => round => participant => submission
    mapping(uint256 => mapping(uint256 => mapping(address => GradientSubmission)))
        public submissions;

    // jobId => round => list of participants
    mapping(uint256 => mapping(uint256 => address[])) public roundParticipants;

    // jobId => round => result
    mapping(uint256 => mapping(uint256 => RoundResult)) public roundResults;

    // jobId => participant => total validated rounds
    mapping(uint256 => mapping(address => uint256)) public participantRounds;

    // jobId => participant => claimed
    mapping(uint256 => mapping(address => bool)) public rewardClaimed;

    // ──────────────────────────────────────
    // Events
    // ──────────────────────────────────────

    event JobCreated(
        uint256 indexed jobId,
        bytes32 modelHash,
        uint256 totalRounds,
        uint256 rewardPool,
        uint256 maxParticipants
    );

    event GradientSubmitted(
        uint256 indexed jobId,
        uint256 indexed round,
        address indexed participant,
        bytes32 gradientHash,
        uint256 dataSize
    );

    event RoundFinalized(
        uint256 indexed jobId,
        uint256 indexed round,
        bytes32 aggregatedHash,
        uint256 participantCount,
        uint256 totalDataSize
    );

    event JobCompleted(uint256 indexed jobId, uint256 totalRounds);
    event JobCancelled(uint256 indexed jobId, uint256 refundAmount);

    event RewardClaimed(
        uint256 indexed jobId,
        address indexed participant,
        uint256 amount
    );

    // ──────────────────────────────────────
    // Constructor
    // ──────────────────────────────────────

    constructor(address _token) Ownable(msg.sender) {
        require(_token != address(0), "Invalid token address");
        token = IERC20(_token);
    }

    // ──────────────────────────────────────
    // Job Management
    // ──────────────────────────────────────

    /**
     * @dev Create a new federated learning training job.
     * @param modelHash Hash of the initial model checkpoint
     * @param totalRounds Number of FedAvg rounds
     * @param rewardAmount Total MDT reward for the entire job
     * @param maxParticipants Maximum participants per round
     * @param roundDeadline Seconds allowed per round
     */
    function createJob(
        bytes32 modelHash,
        uint256 totalRounds,
        uint256 rewardAmount,
        uint256 maxParticipants,
        uint256 roundDeadline
    ) external returns (uint256 jobId) {
        require(totalRounds > 0, "Rounds must be > 0");
        require(rewardAmount > 0, "Reward must be > 0");
        require(maxParticipants > 0, "Max participants must be > 0");
        require(roundDeadline >= 60, "Deadline must be >= 60s");

        // Transfer reward tokens to contract
        token.safeTransferFrom(msg.sender, address(this), rewardAmount);

        jobId = nextJobId++;

        jobs[jobId] = TrainingJob({
            modelHash: modelHash,
            totalRounds: totalRounds,
            currentRound: 1,
            rewardPool: rewardAmount,
            maxParticipants: maxParticipants,
            roundDeadline: roundDeadline,
            status: JobStatus.Active,
            creator: msg.sender,
            createdAt: block.timestamp
        });

        emit JobCreated(
            jobId,
            modelHash,
            totalRounds,
            rewardAmount,
            maxParticipants
        );
    }

    // ──────────────────────────────────────
    // Gradient Submission
    // ──────────────────────────────────────

    /**
     * @dev Submit a gradient hash for the current round of a job.
     * @param jobId The training job ID
     * @param gradientHash Hash of the gradient update (computed off-chain)
     * @param dataSize Number of training samples used
     */
    function submitGradient(
        uint256 jobId,
        bytes32 gradientHash,
        uint256 dataSize
    ) external {
        TrainingJob storage job = jobs[jobId];
        require(job.status == JobStatus.Active, "Job not active");
        require(dataSize > 0, "Data size must be > 0");
        require(gradientHash != bytes32(0), "Invalid gradient hash");

        uint256 round = job.currentRound;
        require(
            submissions[jobId][round][msg.sender].timestamp == 0,
            "Already submitted this round"
        );
        require(
            roundParticipants[jobId][round].length < job.maxParticipants,
            "Round is full"
        );

        submissions[jobId][round][msg.sender] = GradientSubmission({
            gradientHash: gradientHash,
            dataSize: dataSize,
            timestamp: block.timestamp,
            validated: false
        });

        roundParticipants[jobId][round].push(msg.sender);

        emit GradientSubmitted(
            jobId,
            round,
            msg.sender,
            gradientHash,
            dataSize
        );
    }

    // ──────────────────────────────────────
    // Round Finalization (FedAvg)
    // ──────────────────────────────────────

    /**
     * @dev Finalize the current round with the aggregated model hash.
     *      Only the job creator (aggregator) can finalize.
     *      Validates participants and advances to the next round.
     * @param jobId The training job ID
     * @param aggregatedHash The FedAvg result hash
     * @param validParticipants List of participants whose gradients are valid
     */
    function finalizeRound(
        uint256 jobId,
        bytes32 aggregatedHash,
        address[] calldata validParticipants
    ) external {
        TrainingJob storage job = jobs[jobId];
        require(job.status == JobStatus.Active, "Job not active");
        require(msg.sender == job.creator, "Only creator can finalize");
        require(aggregatedHash != bytes32(0), "Invalid aggregated hash");

        uint256 round = job.currentRound;
        require(
            roundParticipants[jobId][round].length > 0,
            "No submissions this round"
        );

        // Mark valid participants
        uint256 totalDataSize = 0;
        for (uint256 i = 0; i < validParticipants.length; i++) {
            address p = validParticipants[i];
            GradientSubmission storage sub = submissions[jobId][round][p];
            require(sub.timestamp > 0, "Participant did not submit");
            sub.validated = true;
            totalDataSize += sub.dataSize;
            participantRounds[jobId][p]++;
        }

        // Store round result
        roundResults[jobId][round] = RoundResult({
            aggregatedHash: aggregatedHash,
            participantCount: validParticipants.length,
            totalDataSize: totalDataSize,
            finalizedAt: block.timestamp
        });

        emit RoundFinalized(
            jobId,
            round,
            aggregatedHash,
            validParticipants.length,
            totalDataSize
        );

        // Advance or complete
        if (round >= job.totalRounds) {
            job.status = JobStatus.Completed;
            emit JobCompleted(jobId, job.totalRounds);
        } else {
            job.currentRound = round + 1;
        }
    }

    // ──────────────────────────────────────
    // Reward Distribution
    // ──────────────────────────────────────

    /**
     * @dev Claim reward for participating in a completed training job.
     *      Reward is proportional to the number of validated rounds.
     * @param jobId The training job ID
     */
    function claimReward(uint256 jobId) external nonReentrant {
        TrainingJob storage job = jobs[jobId];
        require(job.status == JobStatus.Completed, "Job not completed");
        require(!rewardClaimed[jobId][msg.sender], "Already claimed");

        uint256 myRounds = participantRounds[jobId][msg.sender];
        require(myRounds > 0, "No validated contributions");

        // Calculate total participant-rounds across all participants
        uint256 totalParticipantRounds = 0;
        for (uint256 r = 1; r <= job.totalRounds; r++) {
            totalParticipantRounds += roundResults[jobId][r].participantCount;
        }
        require(totalParticipantRounds > 0, "No participants");

        // Proportional reward: myRounds / totalParticipantRounds * rewardPool
        uint256 reward = (job.rewardPool * myRounds) / totalParticipantRounds;
        require(reward > 0, "Reward too small");

        rewardClaimed[jobId][msg.sender] = true;
        token.safeTransfer(msg.sender, reward);

        emit RewardClaimed(jobId, msg.sender, reward);
    }

    // ──────────────────────────────────────
    // Job Cancellation
    // ──────────────────────────────────────

    /**
     * @dev Cancel an active job and refund remaining reward.
     *      Only the job creator can cancel.
     * @param jobId The training job ID
     */
    function cancelJob(uint256 jobId) external nonReentrant {
        TrainingJob storage job = jobs[jobId];
        require(job.status == JobStatus.Active, "Job not active");
        require(msg.sender == job.creator, "Only creator can cancel");

        job.status = JobStatus.Cancelled;

        // Refund remaining reward pool
        uint256 refund = job.rewardPool;
        if (refund > 0) {
            token.safeTransfer(job.creator, refund);
        }

        emit JobCancelled(jobId, refund);
    }

    // ──────────────────────────────────────
    // View Functions
    // ──────────────────────────────────────

    /**
     * @dev Get participants for a specific round of a job.
     */
    function getRoundParticipants(
        uint256 jobId,
        uint256 round
    ) external view returns (address[] memory) {
        return roundParticipants[jobId][round];
    }

    /**
     * @dev Get a participant's submission for a specific round.
     */
    function getSubmission(
        uint256 jobId,
        uint256 round,
        address participant
    )
        external
        view
        returns (
            bytes32 gradientHash,
            uint256 dataSize,
            uint256 timestamp,
            bool validated
        )
    {
        GradientSubmission storage sub = submissions[jobId][round][participant];
        return (sub.gradientHash, sub.dataSize, sub.timestamp, sub.validated);
    }

    /**
     * @dev Get job details.
     */
    function getJobDetails(
        uint256 jobId
    )
        external
        view
        returns (
            bytes32 modelHash,
            uint256 totalRounds,
            uint256 currentRound,
            uint256 rewardPool,
            uint256 maxParticipants,
            JobStatus status,
            address creator
        )
    {
        TrainingJob storage job = jobs[jobId];
        return (
            job.modelHash,
            job.totalRounds,
            job.currentRound,
            job.rewardPool,
            job.maxParticipants,
            job.status,
            job.creator
        );
    }
}
