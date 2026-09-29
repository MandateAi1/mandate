// Behaviour tests for AgentMandate, run against hardhat's in-memory EVM.
//
// The point of these tests is the leash: every way an agent could act outside
// the agreed box must revert, and revocation must be instant and final.
import hre from "hardhat";

let pass = 0, fail = 0;
const results = [];
function check(name, ok, detail = "") {
  if (ok) { pass++; console.log(`  PASS  ${name}`); }
  else { fail++; console.log(`  FAIL  ${name}${detail ? "  -> " + detail : ""}`); }
  results.push({ name, ok, detail });
}

/// Run a call and report whether it reverted, optionally matching the error name.
async function expectRevert(name, promise, errorName) {
  try {
    await promise;
    check(name, false, "did not revert");
  } catch (e) {
    const msg = (e.shortMessage || e.message || "").toString();
    const ok = errorName ? msg.includes(errorName) : true;
    check(name, ok, ok ? "" : `reverted but with: ${msg.slice(0, 90)}`);
  }
}

const conn = await hre.network.connect();
const { ethers } = conn;
const [principal, agent, stranger] = await ethers.getSigners();

const F = await ethers.getContractFactory("AgentMandate");
const c = await F.deploy();
await c.waitForDeployment();

const ZERO = "0x0000000000000000000000000000000000000000";
const SCOPE = ethers.keccak256(ethers.toUtf8Bytes("groceries:read+order"));
const far = Math.floor(Date.now() / 1000) + 86400;

// ---------------------------------------------------------------- granting
console.log("\n-- grant --");
let tx = await c.grant(agent.address, ZERO, 200n, far, SCOPE);
let rc = await tx.wait();
const granted = rc.logs.map((l) => { try { return c.interface.parseLog(l); } catch { return null; } }).filter(Boolean).find((l) => l.name === "MandateGranted");
check("grant emits MandateGranted with correct args",
  !!granted && granted.args[1] === principal.address && granted.args[2] === agent.address && granted.args[4] === 200n,
  granted ? `${granted.args[1]} ${granted.args[2]} ${granted.args[4]}` : "no event");

const id = 1n;
let m = await c.getMandate(id);
check("mandate stores principal/agent/cap/expiry/scope",
  m.principal === principal.address && m.agent === agent.address && m.cap === 200n && m.expiry === BigInt(far) && m.scope === SCOPE && m.revoked === false);
check("remaining() == cap at start", (await c.remaining(id)) === 200n);
check("isLive() true", (await c.isLive(id)) === true);
check("agent can enumerate its mandates", (await c.mandatesOf(agent.address)).length === 1);

await expectRevert("grant with zero agent reverts", c.grant(ZERO, ZERO, 10n, far, SCOPE), "ZeroAgent");
await expectRevert("grant with zero cap reverts", c.grant(stranger.address, ZERO, 0n, far, SCOPE), "CapZero");
await expectRevert("grant with past expiry reverts", c.grant(stranger.address, ZERO, 10n, 1000n, SCOPE), "ExpiryInPast");

// ---------------------------------------------------------------- spending
console.log("\n-- recordAction --");
await (await c.connect(agent).recordAction(id, 50n, SCOPE, "first order")).wait();
m = await c.getMandate(id);
check("spend accumulates", m.spent === 50n);
check("remaining() decreases", (await c.remaining(id)) === 150n);

await (await c.connect(agent).recordAction(id, 150n, SCOPE, "second order")).wait();
check("can spend exactly to the cap", (await c.remaining(id)) === 0n);

await expectRevert("spending past the cap reverts", c.connect(agent).recordAction(id, 1n, SCOPE, "over"), "CapExceeded");
await expectRevert("zero amount reverts", c.connect(agent).recordAction(id, 0n, SCOPE, "zero"), "AmountZero");
await expectRevert("a stranger cannot spend the agent's mandate", c.connect(stranger).recordAction(id, 1n, SCOPE, "nope"), "NotAgent");
await expectRevert("unknown mandate reverts", c.connect(agent).recordAction(999n, 1n, SCOPE, "nope"), "UnknownMandate");

// ---------------------------------------------------------------- revoking
console.log("\n-- revoke --");
await expectRevert("non-principal cannot revoke", c.connect(stranger).revoke(id), "NotPrincipal");
tx = await c.revoke(id);
rc = await tx.wait();
const rev = rc.logs.map((l) => { try { return c.interface.parseLog(l); } catch { return null; } }).filter(Boolean).find((l) => l.name === "MandateRevoked");
check("revoke emits MandateRevoked", !!rev && rev.args[0] === id);
check("revoked mandate is not live", (await c.isLive(id)) === false);
check("remaining() reports 0 once revoked", (await c.remaining(id)) === 0n);
await expectRevert("a revoked mandate cannot be spent", c.connect(agent).recordAction(id, 1n, SCOPE, "after revoke"), "AlreadyRevoked");
await expectRevert("revocation is final (cannot extend back to life)", c.extend(id, 999n, far), "AlreadyRevoked");

// ---------------------------------------------------------------- extending
console.log("\n-- extend --");
const id2 = (await (await c.grant(agent.address, ZERO, 100n, far, SCOPE)).wait())
  .logs.map((l) => { try { return c.interface.parseLog(l); } catch { return null; } }).filter(Boolean).find((l) => l.name === "MandateGranted").args[0];
await (await c.connect(agent).recordAction(id2, 100n, SCOPE, "spend it all")).wait();
check("second mandate exhausted", (await c.remaining(id2)) === 0n);
await (await c.extend(id2, 300n, far)).wait();
check("extend raises the cap", (await c.remaining(id2)) === 200n);
await expectRevert("non-principal cannot extend", c.connect(stranger).extend(id2, 400n, far), "NotPrincipal");
await expectRevert("cannot lower the cap below what is spent", c.extend(id2, 50n, far), "CapZero");

// ---------------------------------------------------------------- expiry
console.log("\n-- expiry --");
const soon = Math.floor(Date.now() / 1000) + 45;   // must outlive the block that mines the grant
const id3 = (await (await c.grant(agent.address, ZERO, 100n, soon, SCOPE)).wait())
  .logs.map((l) => { try { return c.interface.parseLog(l); } catch { return null; } }).filter(Boolean).find((l) => l.name === "MandateGranted").args[0];
check("short-dated mandate starts live", (await c.isLive(id3)) === true);
try {
  // hardhat v3: the connection exposes no provider; the ethers plugin does
  await ethers.provider.send("evm_setNextBlockTimestamp", [soon + 120]);
  await ethers.provider.send("evm_mine", []);
  check("mandate is not live after its expiry", (await c.isLive(id3)) === false);
  await expectRevert("an expired mandate cannot be spent", c.connect(agent).recordAction(id3, 1n, SCOPE, "late"), "MandateExpired");
} catch (e) {
  check("expiry checks", false, "could not advance chain time: " + (e.message || "").slice(0, 80));
}

console.log(`\n  ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
