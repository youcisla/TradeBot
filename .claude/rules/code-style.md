# Code Style Rules

> These rules are enforced on all code written or modified by Claude.

## Formatting
- Use the project's Prettier config. Do not override it.
- Indent with 2 spaces. No tabs.
- Maximum line length: 100 characters.

## Naming Conventions
- Variables and functions: `camelCase`
- Types and interfaces: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Files: `kebab-case`

## General Rules
- Prefer `const` over `let`. Never use `var`.
- No unused variables or imports.
- Avoid deeply nested logic — extract to named functions.
- Write self-documenting code. Add comments only when intent is non-obvious.
