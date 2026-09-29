# Mandate

**Permission slips for AI agents.** Scoped, capped, expiring and revocable authority —
with every action recorded on-chain.

Today an AI agent either holds your credentials (full, permanent power) or it cannot act
at all. Mandate is the middle. A principal grants an agent a bounded mandate; the agent
acts inside it; the chain records both.

## Status

Be precise about what exists:

| Part | State |
|---|---|
| `AgentMandate.sol` — scoped, capped, expiring, revocable permissions | **built, compiles, 20 checks passing** |
| Action record (public event per action) | **built** |
| Agent registry (on-chain identity) | planned |
| Staking to register | planned |
| Slashing for acting outside a mandate | planned |
| Token | **not live** |

The token is not how you pay for this. It is what an agent puts at risk to be allowed to
act — a penalty mechanism, which is the one thing ETH cannot provide, because you cannot
seize ETH the protocol does not hold. That mechanism is not built yet.

## The contract

Solidity 0.8.24, no dependencies, no upgradeability. V1 holds no funds — it is a ledger of
authority, so there is nothing to drain while the design proves out.

```solidity
function grant(address agent, address asset, uint96 cap, uint64 expiry, bytes32 scope)
    external returns (uint256 mandateId);

function recordAction(uint256 mandateId, uint96 amount, bytes32 actionHash, string memo)
    external;                      // reverts outside the box

function revoke(uint256 mandateId) external;   // principal only, final
function extend(uint256 mandateId, uint96 newCap, uint64 newExpiry) external;
```

Every refusal is an explicit custom error — `NotAgent`, `AlreadyRevoked`, `MandateExpired`,
`CapExceeded(requested, remaining)` — so a caller learns exactly which limit it hit.

`remaining()` returns `0` for a revoked or expired mandate, so a dead mandate cannot be
mistaken for a live one. Revocation is final by design: a leash you can quietly re-attach
is not a leash.

## Run it

```bash
npm install
npx hardhat compile
node scripts/mandate-test.mjs
```

```
20 passed, 0 failed
```

The suite covers every way an agent could act outside the box: spending past the cap,
after expiry, after revocation, as the wrong agent, against an unknown mandate, and with a
zero amount. It also checks that a non-principal cannot revoke or extend, and that
revocation cannot be reversed.

## Layout

```
contracts/AgentMandate.sol     the permission ledger
scripts/mandate-test.mjs       behaviour tests, run against an in-memory EVM
brand/make_mark.py             the mark: SVG source plus a raster render
site/index.html                the landing page (self-contained)
```

## Brand

The mark is a monogram in a container: a geometric M inside a rounded square. The
container is the scope, the M is the agent, and the letterform is split vertically through
its centre vertex — the left half in ink, the right in indigo. One structural division
rather than a coloured block stuck on the side.

It is built from four bars — two stems, two diagonals — with the inner vertex *solved* as
the intersection of the two inner edges rather than offset by hand, so the stroke weight is
uniform throughout. The palette follows Linear's system: achromatic surfaces, one accent,
semi-transparent borders.

`brand/make_mark.py` emits both the SVG (the deliverable) and a raster preview from one
shared geometry definition.

## Licence

MIT.
