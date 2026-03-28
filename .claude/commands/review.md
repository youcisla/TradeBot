# /review

Instructs Claude to perform a thorough code review on the current file or selection.

## Behavior
- Analyze the code for correctness, readability, and adherence to project conventions.
- Reference `.claude/rules/code-style.md` and `.claude/rules/api-conventions.md`.
- Output a structured review with sections: **Issues**, **Suggestions**, **Positives**.
- Do not auto-apply fixes — present findings only unless explicitly asked.

## Usage
Type `/review` to trigger a review of the currently open file or selected code block.
