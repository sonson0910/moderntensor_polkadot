// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title SemanticMatchmaker - Gaming Player Matchmaking
 * @notice Match players based on on-chain ELO/skill rating with secure matchmaking
 * @dev Uses pure on-chain ELO + queue-based matchmaking (no precompiles)
 *
 * Use Cases:
 * - Battle Royale: Match players by skill level
 * - MMO: Form balanced raid parties
 * - Esports: Create fair tournament brackets
 * - Cross-game: Portable player reputation
 *
 * Architecture:
 * 1. Players register profiles with on-chain skill rating
 * 2. Matchmaking pairs players with similar ELO ratings
 * 3. Match quality is tracked for feedback loop
 * 4. ELO updates after match completion
 */
contract SemanticMatchmaker is Ownable, ReentrancyGuard {
    // ==================== CONSTANTS ====================

    /// @notice Maximum players per match
    uint256 public constant MAX_PLAYERS_PER_MATCH = 100;

    /// @notice Default ELO rating for new players
    uint256 public constant DEFAULT_RATING = 1000;

    /// @notice ELO K-factor for rating updates
    uint256 public constant ELO_K = 32;

    /// @notice Maximum ELO difference for matching
    uint256 public constant MAX_RATING_DIFF = 300;

    /// @notice Profile update cooldown (blocks)
    uint256 public constant PROFILE_COOLDOWN = 100;

    // ==================== STRUCTS ====================

    /// @notice Player profile
    struct PlayerProfile {
        uint256 skillRating;     // ELO-style rating
        uint256 matchesPlayed;
        uint256 wins;
        uint256 lastUpdated;     // Block number
        bool isActive;
    }

    /// @notice Match information
    struct Match {
        uint256 matchId;
        address[] players;
        uint256 averageRating;
        uint256 createdAt;
        MatchStatus status;
    }

    /// @notice Match status
    enum MatchStatus {
        Pending,
        InProgress,
        Completed,
        Cancelled
    }

    /// @notice Matchmaking request
    struct MatchRequest {
        address player;
        uint256 rating;
        uint256 requestedAt;
        uint256 minPlayers;
        uint256 maxPlayers;
    }

    // ==================== STATE ====================

    /// @notice Player profiles by address
    mapping(address => PlayerProfile) public profiles;

    /// @notice Matches by ID
    mapping(uint256 => Match) public matches;

    /// @notice Pending match requests (queue)
    MatchRequest[] public matchQueue;

    /// @notice Match counter
    uint256 public nextMatchId;

    /// @notice Total registered players
    uint256 public totalPlayers;

    // ==================== EVENTS ====================

    event ProfileRegistered(
        address indexed player,
        uint256 initialRating
    );

    event ProfileUpdated(address indexed player, uint256 newRating);

    event MatchRequested(address indexed player, uint256 queuePosition);

    event MatchCreated(
        uint256 indexed matchId,
        address[] players,
        uint256 averageRating
    );

    event MatchCompleted(
        uint256 indexed matchId,
        address winner,
        uint256 newWinnerRating,
        uint256 newLoserRating
    );

    // ==================== ERRORS ====================

    error ProfileNotFound(address player);
    error ProfileExists(address player);
    error ProfileCooldown(uint256 unlocksAt);
    error AlreadyInQueue(address player);
    error InvalidPlayerCount(uint256 min, uint256 max);
    error MatchNotFound(uint256 matchId);
    error InvalidMatchStatus(uint256 matchId, MatchStatus expected);
    error NotMatchParticipant(address player, uint256 matchId);

    // ==================== CONSTRUCTOR ====================

    /**
     * @notice Initialize matchmaker
     */
    constructor() Ownable(msg.sender) {
        nextMatchId = 1;
    }

    // ==================== PROFILE MANAGEMENT ====================

    /**
     * @notice Register player profile
     * @return rating Initial skill rating
     *
     * @dev Example:
     * ```solidity
     * uint256 myRating = matchmaker.registerProfile();
     * // myRating = 1000 (default ELO)
     * ```
     */
    function registerProfile()
        external
        nonReentrant
        returns (uint256 rating)
    {
        if (profiles[msg.sender].isActive) revert ProfileExists(msg.sender);

        rating = DEFAULT_RATING;
        profiles[msg.sender] = PlayerProfile({
            skillRating: rating,
            matchesPlayed: 0,
            wins: 0,
            lastUpdated: block.number,
            isActive: true
        });

        totalPlayers++;
        emit ProfileRegistered(msg.sender, rating);
    }

    // ==================== MATCHMAKING ====================

    /**
     * @notice Request matchmaking
     * @param minPlayers Minimum players for match
     * @param maxPlayers Maximum players for match
     * @return queuePosition Position in queue
     *
     * @dev Example:
     * ```solidity
     * // Player wants a 2-player (1v1) match
     * uint256 pos = matchmaker.requestMatch(2, 2);
     * ```
     */
    function requestMatch(
        uint256 minPlayers,
        uint256 maxPlayers
    ) external nonReentrant returns (uint256 queuePosition) {
        PlayerProfile storage profile = profiles[msg.sender];
        if (!profile.isActive) revert ProfileNotFound(msg.sender);
        if (
            minPlayers < 2 ||
            maxPlayers > MAX_PLAYERS_PER_MATCH ||
            minPlayers > maxPlayers
        ) {
            revert InvalidPlayerCount(minPlayers, maxPlayers);
        }

        // Check not already in queue
        for (uint256 i = 0; i < matchQueue.length; i++) {
            if (matchQueue[i].player == msg.sender) {
                revert AlreadyInQueue(msg.sender);
            }
        }

        matchQueue.push(
            MatchRequest({
                player: msg.sender,
                rating: profile.skillRating,
                requestedAt: block.timestamp,
                minPlayers: minPlayers,
                maxPlayers: maxPlayers
            })
        );

        queuePosition = matchQueue.length;
        emit MatchRequested(msg.sender, queuePosition);

        // Try to form a match
        _tryFormMatch();
    }

    /**
     * @notice Report match result and update ELO ratings
     * @param matchId Match ID
     * @param winner Winner address
     */
    function reportResult(
        uint256 matchId,
        address winner
    ) external onlyOwner nonReentrant {
        Match storage m = matches[matchId];
        if (m.matchId == 0) revert MatchNotFound(matchId);
        if (m.status != MatchStatus.Pending) {
            revert InvalidMatchStatus(matchId, MatchStatus.Pending);
        }

        // Verify winner is a participant
        bool found = false;
        for (uint256 i = 0; i < m.players.length; i++) {
            if (m.players[i] == winner) {
                found = true;
                break;
            }
        }
        if (!found) revert NotMatchParticipant(winner, matchId);

        // Update ELO for all participants
        PlayerProfile storage winnerProfile = profiles[winner];
        winnerProfile.wins++;

        // Update ratings: winner gains, others lose
        for (uint256 i = 0; i < m.players.length; i++) {
            PlayerProfile storage p = profiles[m.players[i]];
            p.matchesPlayed++;

            if (m.players[i] == winner) {
                // Winner gains ELO based on average opponent rating
                uint256 gain = _calculateEloChange(
                    p.skillRating,
                    m.averageRating,
                    true
                );
                p.skillRating += gain;
            } else {
                // Losers lose ELO
                uint256 loss = _calculateEloChange(
                    p.skillRating,
                    m.averageRating,
                    false
                );
                p.skillRating = p.skillRating > loss
                    ? p.skillRating - loss
                    : 100; // Floor at 100
            }
            p.lastUpdated = block.number;
        }

        m.status = MatchStatus.Completed;

        emit MatchCompleted(
            matchId,
            winner,
            profiles[winner].skillRating,
            m.averageRating
        );
    }

    // ==================== INTERNAL FUNCTIONS ====================

    /**
     * @dev Attempt to form a match from queued players based on ELO proximity
     */
    function _tryFormMatch() internal {
        if (matchQueue.length < 2) return;

        MatchRequest memory first = matchQueue[0];

        // Find compatible players (within MAX_RATING_DIFF of first player)
        address[] memory matchedPlayers = new address[](first.maxPlayers);
        uint256 matchedCount = 1;
        matchedPlayers[0] = first.player;

        uint256[] memory toRemove = new uint256[](matchQueue.length);
        uint256 removeCount = 1;
        toRemove[0] = 0;

        for (
            uint256 i = 1;
            i < matchQueue.length && matchedCount < first.maxPlayers;
            i++
        ) {
            MatchRequest memory candidate = matchQueue[i];

            // Check ELO compatibility
            uint256 ratingDiff = first.rating > candidate.rating
                ? first.rating - candidate.rating
                : candidate.rating - first.rating;

            if (
                ratingDiff <= MAX_RATING_DIFF &&
                candidate.minPlayers <= first.maxPlayers
            ) {
                matchedPlayers[matchedCount] = candidate.player;
                matchedCount++;
                toRemove[removeCount++] = i;
            }
        }

        // Check if we have enough players
        if (matchedCount >= first.minPlayers) {
            // Trim arrays
            address[] memory finalPlayers = new address[](matchedCount);
            uint256 totalRating = 0;

            for (uint256 i = 0; i < matchedCount; i++) {
                finalPlayers[i] = matchedPlayers[i];
                totalRating += profiles[matchedPlayers[i]].skillRating;
            }

            // Create match
            uint256 matchId = nextMatchId++;
            matches[matchId] = Match({
                matchId: matchId,
                players: finalPlayers,
                averageRating: totalRating / matchedCount,
                createdAt: block.timestamp,
                status: MatchStatus.Pending
            });

            // Remove from queue (from end to avoid index shifting issues)
            for (uint256 i = removeCount; i > 0; i--) {
                _removeFromQueue(toRemove[i - 1]);
            }

            emit MatchCreated(
                matchId,
                finalPlayers,
                totalRating / matchedCount
            );
        }
    }

    /**
     * @dev Calculate ELO rating change
     * @param playerRating Current player rating
     * @param opponentRating Opponent (or average opponent) rating
     * @param won Whether the player won
     * @return change Rating change amount
     */
    function _calculateEloChange(
        uint256 playerRating,
        uint256 opponentRating,
        bool won
    ) internal pure returns (uint256 change) {
        // Simplified ELO: K * |difference factor|
        // Higher diff when beating stronger opponents, lower when beating weaker
        if (won) {
            if (opponentRating >= playerRating) {
                // Beat a stronger or equal player: gain more
                change = ELO_K + (opponentRating - playerRating) / 10;
            } else {
                // Beat a weaker player: gain less
                uint256 diff = playerRating - opponentRating;
                change = diff >= ELO_K * 10 ? 1 : ELO_K - diff / 10;
            }
        } else {
            if (playerRating >= opponentRating) {
                // Lost to a weaker player: lose more
                change = ELO_K + (playerRating - opponentRating) / 10;
            } else {
                // Lost to a stronger player: lose less
                uint256 diff = opponentRating - playerRating;
                change = diff >= ELO_K * 10 ? 1 : ELO_K - diff / 10;
            }
        }
    }

    /**
     * @dev Remove player from queue by index
     */
    function _removeFromQueue(uint256 index) internal {
        require(index < matchQueue.length, "Invalid index");
        matchQueue[index] = matchQueue[matchQueue.length - 1];
        matchQueue.pop();
    }

    // ==================== VIEW FUNCTIONS ====================

    /**
     * @notice Get player profile
     * @param player Player address
     * @return Profile data
     */
    function getProfile(
        address player
    ) external view returns (PlayerProfile memory) {
        return profiles[player];
    }

    /**
     * @notice Get queue length
     * @return Current queue size
     */
    function getQueueLength() external view returns (uint256) {
        return matchQueue.length;
    }

    /**
     * @notice Get match details
     * @param matchId Match ID
     * @return Match data
     */
    function getMatch(uint256 matchId) external view returns (Match memory) {
        return matches[matchId];
    }

    /**
     * @notice Get player's win rate (scaled by 1e18)
     * @param player Player address
     * @return winRate Win rate (0 to 1e18)
     */
    function getWinRate(address player) external view returns (uint256 winRate) {
        PlayerProfile storage p = profiles[player];
        if (p.matchesPlayed == 0) return 0;
        winRate = (p.wins * 1e18) / p.matchesPlayed;
    }
}
