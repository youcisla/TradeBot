# Prompt Improvement Tips From Session Analysis

Generated: 2026-04-04
Scope: 2 analyzed conversations in Antigravity brain

## What to Add Up Front

1) Privilege and policy assumptions
- State whether admin elevation is available.
- State whether corporate Windows policy blocks unsigned binaries.

2) Environment and dependency preflight
- Specify which package managers are permitted and preferred.
- Confirm required toolchain baseline before implementation (example: go, make).

3) Acceptance tiers
- Tier 1: code change compiles/builds.
- Tier 2: tests pass.
- Tier 3: runtime execution on host policy.

4) Scope boundary and carry-over rule
- Include one line for non-goals.
- If objective changes between sessions, add a carry-over note naming:
  - prior objective,
  - new objective,
  - reason for expansion.

## Reusable Prompt Template

Use this structure for Windows build or setup tasks:

- Objective: one sentence with final expected state
- File targets: explicit paths to edit
- Allowed tools/installers: winget/choco/scoop/manual
- Constraints: admin access yes/no, policy restrictions yes/no
- Non-goals: what should not be changed
- Validation:
  - required commands
  - expected outputs
  - fallback if policy blocks execution

## Example Upgrade

Before:
Install make and add to PATH.

After:
Install make on Windows using winget or choco (no manual registry edits). Assume admin access is unavailable unless confirmed. Do not change unrelated project files. Validate with make --version and where make. If package-manager install is blocked, stop and provide a manual no-admin fallback path.

## Expected Impact

- Lower abandoned-mid-flight rate on setup tasks
- Lower replan intensity caused by late constraint discovery
- Better distinction between code success and host-policy blockers
