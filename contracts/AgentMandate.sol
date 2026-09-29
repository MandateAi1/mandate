// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title AgentMandate
/// @notice A permission slip for an AI agent: scoped, capped, expiring, revocable.
///
/// The problem this solves: today an agent either gets your credentials (full,
/// permanent power) or nothing. There is no middle. This contract is the middle.
///
/// A principal grants an agent a mandate — an asset, a spending cap, an expiry
/// and an opaque scope hash naming what the agent is allowed to do. The agent
/// then records each action against the mandate. Every action is a public event,
/// so the record is evidence rather than a claim.
///
/// V1 is deliberately a LEDGER, not a custodian: no funds move through it, so
/// there is nothing to drain while the design proves out. Escrow and staking come
/// after this is right.
contract AgentMandate {
    // ------------------------------------------------------------------ types

    struct Mandate {
        address principal;   // who granted it; the only address that can revoke
        address agent;       // who may act under it
        address asset;       // what may be spent (address(0) = native)
        uint96  cap;         // maximum total, in the asset's smallest unit
        uint96  spent;       // running total
        uint64  expiry;      // unix seconds; 0 = no expiry
        bool    revoked;
        bytes32 scope;       // opaque action-scope hash agreed off-chain
    }

    // ----------------------------------------------------------------- errors

    error NotPrincipal();
    error NotAgent();
    error UnknownMandate();
    error AlreadyRevoked();
    error MandateExpired();
    error CapExceeded(uint256 requested, uint256 remaining);
    error ZeroAgent();
    error CapZero();
    error ExpiryInPast();
    error AmountZero();

    // ----------------------------------------------------------------- events

    event MandateGranted(
        uint256 indexed mandateId,
        address indexed principal,
        address indexed agent,
        address asset,
        uint96 cap,
        uint64 expiry,
        bytes32 scope
    );

    /// The accountability record. Every agent action lands here, in order.
    event ActionRecorded(
        uint256 indexed mandateId,
        address indexed agent,
        uint96 amount,
        uint96 spentAfter,
        bytes32 actionHash,
        string memo
    );

    event MandateRevoked(uint256 indexed mandateId, address indexed by);
    event MandateExtended(uint256 indexed mandateId, uint96 newCap, uint64 newExpiry);

    // ----------------------------------------------------------------- state

    uint256 public nextMandateId = 1;
    mapping(uint256 => Mandate) private _mandates;

    /// mandate ids per agent, so an agent can enumerate what it may do
    mapping(address => uint256[]) private _agentMandates;

    // ----------------------------------------------------------------- writes

    /// Grant a mandate. The caller becomes the principal.
    function grant(
        address agent,
        address asset,
        uint96 cap,
        uint64 expiry,
        bytes32 scope
    ) external returns (uint256 mandateId) {
        if (agent == address(0)) revert ZeroAgent();
        if (cap == 0) revert CapZero();
        if (expiry != 0 && expiry <= block.timestamp) revert ExpiryInPast();

        mandateId = nextMandateId++;
        _mandates[mandateId] = Mandate({
            principal: msg.sender,
            agent: agent,
            asset: asset,
            cap: cap,
            spent: 0,
            expiry: expiry,
            revoked: false,
            scope: scope
        });
        _agentMandates[agent].push(mandateId);

        emit MandateGranted(mandateId, msg.sender, agent, asset, cap, expiry, scope);
    }

    /// Record an action by the agent against its mandate.
    ///
    /// This is the whole point: it either succeeds inside the agreed box, or it
    /// reverts. There is no path where the agent acts outside the mandate and the
    /// record shows it as allowed.
    function recordAction(
        uint256 mandateId,
        uint96 amount,
        bytes32 actionHash,
        string calldata memo
    ) external {
        Mandate storage m = _mandates[mandateId];
        if (m.principal == address(0)) revert UnknownMandate();
        if (msg.sender != m.agent) revert NotAgent();
        if (m.revoked) revert AlreadyRevoked();
        if (m.expiry != 0 && block.timestamp > m.expiry) revert MandateExpired();
        if (amount == 0) revert AmountZero();

        uint256 left = uint256(m.cap) - uint256(m.spent);
        if (amount > left) revert CapExceeded(amount, left);

        m.spent += amount;
        emit ActionRecorded(mandateId, msg.sender, amount, m.spent, actionHash, memo);
    }

    /// Revoke instantly. Only the principal can, and it takes effect immediately.
    function revoke(uint256 mandateId) external {
        Mandate storage m = _mandates[mandateId];
        if (m.principal == address(0)) revert UnknownMandate();
        if (msg.sender != m.principal) revert NotPrincipal();
        m.revoked = true;
        emit MandateRevoked(mandateId, msg.sender);
    }

    /// Raise the cap or push the expiry out. Cannot un-revoke: revocation is final
    /// by design, because a leash you can quietly re-attach is not a leash.
    function extend(uint256 mandateId, uint96 newCap, uint64 newExpiry) external {
        Mandate storage m = _mandates[mandateId];
        if (m.principal == address(0)) revert UnknownMandate();
        if (msg.sender != m.principal) revert NotPrincipal();
        if (m.revoked) revert AlreadyRevoked();
        if (newCap < m.spent) revert CapZero();
        if (newExpiry != 0 && newExpiry <= block.timestamp) revert ExpiryInPast();

        m.cap = newCap;
        m.expiry = newExpiry;
        emit MandateExtended(mandateId, newCap, newExpiry);
    }

    // ----------------------------------------------------------------- views

    function getMandate(uint256 mandateId) external view returns (Mandate memory) {
        return _mandates[mandateId];
    }

    /// The remaining allowance, accounting for expiry and revocation. Returns 0
    /// once a mandate can no longer be used, so a caller cannot mistake a dead
    /// mandate for a live one.
    function remaining(uint256 mandateId) external view returns (uint256) {
        Mandate storage m = _mandates[mandateId];
        if (m.principal == address(0) || m.revoked) return 0;
        if (m.expiry != 0 && block.timestamp > m.expiry) return 0;
        return uint256(m.cap) - uint256(m.spent);
    }

    function isLive(uint256 mandateId) external view returns (bool) {
        Mandate storage m = _mandates[mandateId];
        if (m.principal == address(0) || m.revoked) return false;
        if (m.expiry != 0 && block.timestamp > m.expiry) return false;
        return true;
    }

    function mandatesOf(address agent) external view returns (uint256[] memory) {
        return _agentMandates[agent];
    }
}
