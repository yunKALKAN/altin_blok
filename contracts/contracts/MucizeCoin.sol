// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import "@openzeppelin/contracts/access/Ownable2Step.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title MucizeCoin (MZC)
 * @author Mimar Yonus KALKAN — mucizeWORK Ekosistemi
 * @notice ERC-20 token for the mucizeWORK ecosystem.
 *
 *  Total supply : 1,000,000,000 MZC (1 Billion)
 *  Decimals     : 18
 *
 *  Features:
 *    - Ownable2Step  (safe ownership transfer, Gnosis Safe compatible)
 *    - Burnable      (LP token burn, deflationary mechanics)
 *    - Pausable      (emergency circuit-breaker)
 *    - Permit        (gasless approvals via EIP-2612)
 *    - Capped mint   (owner can mint up to MAX_SUPPLY)
 */
contract MucizeCoin is ERC20, ERC20Burnable, ERC20Permit, Ownable2Step, Pausable {
    uint256 public constant MAX_SUPPLY = 1_000_000_000 * 10 ** 18; // 1 Billion MZC

    constructor(address initialOwner)
        ERC20("MucizeCoin", "MZC")
        ERC20Permit("MucizeCoin")
        Ownable(initialOwner)
    {
        _mint(initialOwner, MAX_SUPPLY);
    }

    /**
     * @notice Mint new tokens (only below MAX_SUPPLY cap).
     * @dev    Can only be called by the contract owner.
     */
    function mint(address to, uint256 amount) external onlyOwner {
        require(totalSupply() + amount <= MAX_SUPPLY, "MZC: cap exceeded");
        _mint(to, amount);
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    function _update(address from, address to, uint256 value)
        internal
        override
        whenNotPaused
    {
        super._update(from, to, value);
    }
}
