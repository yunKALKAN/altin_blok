// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable2Step.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title MZCVesting
 * @author Mimar Yonus KALKAN — mucizeWORK Ekosistemi
 * @notice Linear vesting with cliff for MZC token allocations.
 *
 *  Supported schedules (from tokenomics):
 *    - Team & Founder  : 6-month cliff + 18-month linear vesting
 *    - Investor/Presale: 3-month cliff + 12-month linear vesting
 *    - Advisors        : 6-month cliff + 12-month linear vesting
 *    - Ecosystem       : 12-month linear vesting (no cliff)
 */
contract MZCVesting is Ownable2Step, ReentrancyGuard {
    using SafeERC20 for IERC20;

    struct VestingSchedule {
        uint256 totalAmount;
        uint256 released;
        uint64  start;
        uint64  cliffDuration;   // seconds
        uint64  vestingDuration; // seconds (after cliff)
        bool    revoked;
    }

    IERC20 public immutable token;

    mapping(address => VestingSchedule[]) private _schedules;
    uint256 public totalAllocated;

    event ScheduleCreated(
        address indexed beneficiary,
        uint256 index,
        uint256 totalAmount,
        uint64  start,
        uint64  cliffDuration,
        uint64  vestingDuration
    );
    event TokensReleased(address indexed beneficiary, uint256 index, uint256 amount);
    event ScheduleRevoked(address indexed beneficiary, uint256 index, uint256 refunded);

    constructor(address tokenAddress, address initialOwner) Ownable(initialOwner) {
        require(tokenAddress != address(0), "Vesting: zero token");
        token = IERC20(tokenAddress);
    }

    /**
     * @notice Create a new vesting schedule.
     * @param beneficiary   Wallet that will receive vested tokens.
     * @param totalAmount   Total MZC to vest.
     * @param start         Unix timestamp when vesting begins.
     * @param cliffDuration Seconds before first release (0 = no cliff).
     * @param vestingDuration Seconds of linear vesting after cliff.
     */
    function createSchedule(
        address beneficiary,
        uint256 totalAmount,
        uint64  start,
        uint64  cliffDuration,
        uint64  vestingDuration
    ) external onlyOwner {
        require(beneficiary != address(0), "Vesting: zero address");
        require(totalAmount > 0, "Vesting: zero amount");
        require(vestingDuration > 0, "Vesting: zero duration");

        token.safeTransferFrom(msg.sender, address(this), totalAmount);
        totalAllocated += totalAmount;

        uint256 idx = _schedules[beneficiary].length;
        _schedules[beneficiary].push(VestingSchedule({
            totalAmount: totalAmount,
            released: 0,
            start: start,
            cliffDuration: cliffDuration,
            vestingDuration: vestingDuration,
            revoked: false
        }));

        emit ScheduleCreated(beneficiary, idx, totalAmount, start, cliffDuration, vestingDuration);
    }

    /**
     * @notice Release vested tokens for a specific schedule.
     */
    function release(uint256 index) external nonReentrant {
        VestingSchedule storage s = _schedules[msg.sender][index];
        require(!s.revoked, "Vesting: revoked");

        uint256 vested = _vestedAmount(s);
        uint256 unreleased = vested - s.released;
        require(unreleased > 0, "Vesting: nothing to release");

        s.released += unreleased;
        token.safeTransfer(msg.sender, unreleased);

        emit TokensReleased(msg.sender, index, unreleased);
    }

    /**
     * @notice Revoke a schedule — unreleased tokens go back to owner.
     */
    function revoke(address beneficiary, uint256 index) external onlyOwner {
        VestingSchedule storage s = _schedules[beneficiary][index];
        require(!s.revoked, "Vesting: already revoked");

        uint256 vested = _vestedAmount(s);
        uint256 unreleased = vested - s.released;
        uint256 refund = s.totalAmount - vested;

        s.revoked = true;

        if (unreleased > 0) {
            s.released += unreleased;
            token.safeTransfer(beneficiary, unreleased);
        }
        if (refund > 0) {
            totalAllocated -= refund;
            token.safeTransfer(owner(), refund);
        }

        emit ScheduleRevoked(beneficiary, index, refund);
    }

    // ── View helpers ──────────────────────────────────────────────

    function scheduleCount(address beneficiary) external view returns (uint256) {
        return _schedules[beneficiary].length;
    }

    function getSchedule(address beneficiary, uint256 index)
        external
        view
        returns (VestingSchedule memory)
    {
        return _schedules[beneficiary][index];
    }

    function releasable(address beneficiary, uint256 index) external view returns (uint256) {
        VestingSchedule storage s = _schedules[beneficiary][index];
        if (s.revoked) return 0;
        return _vestedAmount(s) - s.released;
    }

    // ── Internal ──────────────────────────────────────────────────

    function _vestedAmount(VestingSchedule storage s) private view returns (uint256) {
        if (block.timestamp < s.start + s.cliffDuration) {
            return 0;
        }
        uint256 elapsed = block.timestamp - s.start - s.cliffDuration;
        if (elapsed >= s.vestingDuration) {
            return s.totalAmount;
        }
        return (s.totalAmount * elapsed) / s.vestingDuration;
    }
}
