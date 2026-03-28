# /fix-issue

Takes a described issue or bug and applies a targeted fix.

## Behavior
- Ask for the issue description if not provided.
- Identify the root cause before applying any changes.
- Apply the minimal diff necessary to resolve the issue.
- Respect code style rules defined in `.claude/rules/code-style.md`.
- After applying the fix, summarize what was changed and why.

## Usage
Type `/fix-issue` followed by a brief description of the problem, or select the problematic code first.
