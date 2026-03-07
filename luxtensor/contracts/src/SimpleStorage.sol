// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title SimpleStorage - Minimal test contract for Westend AssetHub deployment
contract SimpleStorage {
    uint256 public value;
    address public owner;

    event ValueSet(uint256 newValue, address setter);

    constructor() {
        owner = msg.sender;
        value = 42;
    }

    function setValue(uint256 _value) external {
        value = _value;
        emit ValueSet(_value, msg.sender);
    }
}
