// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title TrainingEscrow
 * @dev Escrow contract for decentralized AI training on Polkadot Hub (pallet-revive EVM).
 *
 * Flow:
 *   1. Trainers stake MDT tokens to participate in training tasks.
 *   2. Task creators deposit rewards into escrow.
 *   3. After training, the verifier (owner/ZkMLVerifier) validates results.
 *   4. Valid trainers receive rewards; invalid trainers get slashed.
 *
 * Integrates with GradientAggregator for federated learning workflows
 * and ZkMLVerifier for proof-based validation.
 */
contract TrainingEscrow is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    // ──────────────────────────────────────
    // Data Structures
    // ──────────────────────────────────────

    enum TaskStatus {
        Open,
        InProgress,
        Completed,
        Cancelled
    }

    struct TrainingTask {
        address creator;
        bytes32 modelHash; // Hash of the model to train
        uint256 rewardAmount; // Total reward in MDT
        uint256 minStake; // Minimum stake required to participate
        uint256 maxTrainers; // Maximum number of trainers
        uint256 deadline; // Task deadline timestamp
        TaskStatus status;
        uint256 createdAt;
    }

    struct TrainerInfo {
        uint256 stakeAmount; // Amount staked for this task
        bool submitted; // Whether training result was submitted
        bool validated; // Whether result passed validation
        bool slashed; // Whether trainer was slashed
        bool rewardClaimed; // Whether reward was claimed
        bytes32 resultHash; // Hash of the training result
        uint256 submittedAt;
    }

    // ──────────────────────────────────────
    // State
    // ──────────────────────────────────────

    IERC20 public immutable token;

    uint256 public nextTaskId;
    uint256 public slashRate; // Slash rate in basis points (e.g., 5000 = 50%)
    uint256 public totalSlashed; // Total MDT slashed across all tasks

    mapping(uint256 => TrainingTask) public tasks;

    // taskId => trainer => info
    mapping(uint256 => mapping(address => TrainerInfo)) public trainers;

    // taskId => list of trainer addresses
    mapping(uint256 => address[]) public taskTrainers;

    // ──────────────────────────────────────
    // Events
    // ──────────────────────────────────────

    event TaskCreated(
        uint256 indexed taskId,
        address indexed creator,
        bytes32 modelHash,
        uint256 rewardAmount,
        uint256 minStake,
        uint256 deadline
    );

    event TrainerJoined(
        uint256 indexed taskId,
        address indexed trainer,
        uint256 stakeAmount
    );

    event ResultSubmitted(
        uint256 indexed taskId,
        address indexed trainer,
        bytes32 resultHash
    );

    event TrainerValidated(
        uint256 indexed taskId,
        address indexed trainer,
        bool isValid
    );

    event TrainerSlashed(
        uint256 indexed taskId,
        address indexed trainer,
        uint256 slashAmount
    );

    event RewardDistributed(
        uint256 indexed taskId,
        address indexed trainer,
        uint256 rewardAmount,
        uint256 stakeReturned
    );

    event TaskCompleted(uint256 indexed taskId);
    event TaskCancelled(uint256 indexed taskId, uint256 refundAmount);

    // ──────────────────────────────────────
    // Constructor
    // ──────────────────────────────────────

    /**
     * @param _token MDT token address
     * @param _slashRate Slash rate in basis points (e.g., 5000 = 50%)
     */
    constructor(address _token, uint256 _slashRate) Ownable(msg.sender) {
        require(_token != address(0), "Invalid token address");
        require(_slashRate <= 10000, "Slash rate exceeds 100%");
        token = IERC20(_token);
        slashRate = _slashRate;
    }

    // ──────────────────────────────────────
    // Task Management
    // ──────────────────────────────────────

    /**
     * @dev Create a new training task with escrowed rewards.
     * @param modelHash Hash of the model checkpoint
     * @param rewardAmount Total reward in MDT tokens
     * @param minStake Minimum stake required from each trainer
     * @param maxTrainers Maximum number of trainers
     * @param durationSeconds Duration of the task in seconds
     */
    function createTask(
        bytes32 modelHash,
        uint256 rewardAmount,
        uint256 minStake,
        uint256 maxTrainers,
        uint256 durationSeconds
    ) external returns (uint256 taskId) {
        require(rewardAmount > 0, "Reward must be > 0");
        require(minStake > 0, "Min stake must be > 0");
        require(maxTrainers > 0, "Max trainers must be > 0");
        require(durationSeconds >= 300, "Duration must be >= 5 minutes");

        // Transfer reward to escrow
        token.safeTransferFrom(msg.sender, address(this), rewardAmount);

        taskId = nextTaskId++;

        tasks[taskId] = TrainingTask({
            creator: msg.sender,
            modelHash: modelHash,
            rewardAmount: rewardAmount,
            minStake: minStake,
            maxTrainers: maxTrainers,
            deadline: block.timestamp + durationSeconds,
            status: TaskStatus.Open,
            createdAt: block.timestamp
        });

        emit TaskCreated(
            taskId,
            msg.sender,
            modelHash,
            rewardAmount,
            minStake,
            block.timestamp + durationSeconds
        );
    }

    // ──────────────────────────────────────
    // Trainer Operations
    // ──────────────────────────────────────

    /**
     * @dev Join a training task by staking MDT tokens.
     * @param taskId The task to join
     * @param stakeAmount Amount of MDT to stake (must be >= minStake)
     */
    function joinTask(uint256 taskId, uint256 stakeAmount) external {
        TrainingTask storage task = tasks[taskId];
        require(
            task.status == TaskStatus.Open ||
                task.status == TaskStatus.InProgress,
            "Task not accepting trainers"
        );
        require(block.timestamp < task.deadline, "Task expired");
        require(stakeAmount >= task.minStake, "Stake below minimum");
        require(
            trainers[taskId][msg.sender].stakeAmount == 0,
            "Already joined"
        );
        require(taskTrainers[taskId].length < task.maxTrainers, "Task is full");

        token.safeTransferFrom(msg.sender, address(this), stakeAmount);

        trainers[taskId][msg.sender] = TrainerInfo({
            stakeAmount: stakeAmount,
            submitted: false,
            validated: false,
            slashed: false,
            rewardClaimed: false,
            resultHash: bytes32(0),
            submittedAt: 0
        });

        taskTrainers[taskId].push(msg.sender);

        // Move to InProgress when first trainer joins
        if (task.status == TaskStatus.Open) {
            task.status = TaskStatus.InProgress;
        }

        emit TrainerJoined(taskId, msg.sender, stakeAmount);
    }

    /**
     * @dev Submit training result hash.
     * @param taskId The task ID
     * @param resultHash Hash of the training result (model weights, gradients, etc.)
     */
    function submitResult(uint256 taskId, bytes32 resultHash) external {
        TrainingTask storage task = tasks[taskId];
        require(task.status == TaskStatus.InProgress, "Task not in progress");
        require(block.timestamp <= task.deadline, "Task expired");

        TrainerInfo storage trainer = trainers[taskId][msg.sender];
        require(trainer.stakeAmount > 0, "Not a participant");
        require(!trainer.submitted, "Already submitted");
        require(resultHash != bytes32(0), "Invalid result hash");

        trainer.submitted = true;
        trainer.resultHash = resultHash;
        trainer.submittedAt = block.timestamp;

        emit ResultSubmitted(taskId, msg.sender, resultHash);
    }

    // ──────────────────────────────────────
    // Validation & Slashing
    // ──────────────────────────────────────

    /**
     * @dev Validate a trainer's submission (owner/verifier only).
     *      Invalid submissions are slashed.
     * @param taskId The task ID
     * @param trainer The trainer address
     * @param isValid Whether the submission is valid
     */
    function validateTrainer(
        uint256 taskId,
        address trainer,
        bool isValid
    ) external onlyOwner {
        TrainingTask storage task = tasks[taskId];
        require(
            task.status == TaskStatus.InProgress ||
                task.status == TaskStatus.Open,
            "Task already finalized"
        );

        TrainerInfo storage info = trainers[taskId][trainer];
        require(info.stakeAmount > 0, "Not a participant");
        require(info.submitted, "No submission to validate");
        require(!info.validated && !info.slashed, "Already processed");

        if (isValid) {
            info.validated = true;
            emit TrainerValidated(taskId, trainer, true);
        } else {
            // Slash the trainer
            info.slashed = true;
            uint256 slashAmount = (info.stakeAmount * slashRate) / 10000;
            totalSlashed += slashAmount;

            // Return remaining stake (after slash)
            uint256 remaining = info.stakeAmount - slashAmount;
            if (remaining > 0) {
                token.safeTransfer(trainer, remaining);
            }

            emit TrainerSlashed(taskId, trainer, slashAmount);
            emit TrainerValidated(taskId, trainer, false);
        }
    }

    /**
     * @dev Complete the task and allow validated trainers to claim rewards.
     *      Only callable by owner after all validations are done.
     * @param taskId The task ID
     */
    function completeTask(uint256 taskId) external onlyOwner {
        TrainingTask storage task = tasks[taskId];
        require(task.status == TaskStatus.InProgress, "Task not in progress");

        task.status = TaskStatus.Completed;
        emit TaskCompleted(taskId);
    }

    /**
     * @dev Claim reward for a completed task (validated trainers only).
     * @param taskId The task ID
     */
    function claimReward(uint256 taskId) external nonReentrant {
        TrainingTask storage task = tasks[taskId];
        require(task.status == TaskStatus.Completed, "Task not completed");

        TrainerInfo storage info = trainers[taskId][msg.sender];
        require(info.validated, "Not validated");
        require(!info.rewardClaimed, "Already claimed");

        // Count validated trainers for proportional distribution
        uint256 validCount = 0;
        address[] storage trainerList = taskTrainers[taskId];
        for (uint256 i = 0; i < trainerList.length; i++) {
            if (trainers[taskId][trainerList[i]].validated) {
                validCount++;
            }
        }
        require(validCount > 0, "No validated trainers");

        // Proportional reward
        uint256 reward = task.rewardAmount / validCount;
        info.rewardClaimed = true;

        // Return stake + reward
        uint256 stakeReturn = info.stakeAmount;
        token.safeTransfer(msg.sender, stakeReturn + reward);

        emit RewardDistributed(taskId, msg.sender, reward, stakeReturn);
    }

    // ──────────────────────────────────────
    // Task Cancellation
    // ──────────────────────────────────────

    /**
     * @dev Cancel a task and refund.
     *      - If no trainers: full refund to creator.
     *      - If trainers exist: only creator (or owner after deadline) can cancel.
     * @param taskId The task ID
     */
    function cancelTask(uint256 taskId) external nonReentrant {
        TrainingTask storage task = tasks[taskId];
        require(
            task.status == TaskStatus.Open ||
                task.status == TaskStatus.InProgress,
            "Task already finalized"
        );

        bool isCreator = msg.sender == task.creator;
        bool isOwnerAfterDeadline = msg.sender == owner() &&
            block.timestamp > task.deadline;
        require(isCreator || isOwnerAfterDeadline, "Not authorized");

        task.status = TaskStatus.Cancelled;

        // Refund stakes to all trainers
        address[] storage trainerList = taskTrainers[taskId];
        for (uint256 i = 0; i < trainerList.length; i++) {
            TrainerInfo storage info = trainers[taskId][trainerList[i]];
            if (info.stakeAmount > 0 && !info.slashed && !info.rewardClaimed) {
                uint256 stake = info.stakeAmount;
                info.stakeAmount = 0;
                token.safeTransfer(trainerList[i], stake);
            }
        }

        // Refund reward to creator
        if (task.rewardAmount > 0) {
            token.safeTransfer(task.creator, task.rewardAmount);
        }

        emit TaskCancelled(taskId, task.rewardAmount);
    }

    // ──────────────────────────────────────
    // Admin
    // ──────────────────────────────────────

    /**
     * @dev Update the slash rate.
     * @param newRate New slash rate in basis points (max 10000)
     */
    function setSlashRate(uint256 newRate) external onlyOwner {
        require(newRate <= 10000, "Rate exceeds 100%");
        slashRate = newRate;
    }

    /**
     * @dev Withdraw slashed tokens (treasury).
     */
    function withdrawSlashed(address to) external onlyOwner nonReentrant {
        require(to != address(0), "Invalid address");
        require(totalSlashed > 0, "No slashed funds");

        uint256 amount = totalSlashed;
        totalSlashed = 0;
        token.safeTransfer(to, amount);
    }

    // ──────────────────────────────────────
    // View Functions
    // ──────────────────────────────────────

    /**
     * @dev Get all trainers for a task.
     */
    function getTaskTrainers(
        uint256 taskId
    ) external view returns (address[] memory) {
        return taskTrainers[taskId];
    }

    /**
     * @dev Get task details.
     */
    function getTaskDetails(
        uint256 taskId
    )
        external
        view
        returns (
            address creator,
            bytes32 modelHash,
            uint256 rewardAmount,
            uint256 minStake,
            uint256 maxTrainers,
            uint256 deadline,
            TaskStatus status,
            uint256 trainerCount
        )
    {
        TrainingTask storage task = tasks[taskId];
        return (
            task.creator,
            task.modelHash,
            task.rewardAmount,
            task.minStake,
            task.maxTrainers,
            task.deadline,
            task.status,
            taskTrainers[taskId].length
        );
    }
}
