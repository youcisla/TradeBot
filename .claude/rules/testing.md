# Testing Rules

> These rules define how tests must be written across the project.

## Framework
- Use [e.g. Vitest / Jest] as the test runner.

## Structure
- Co-locate unit tests next to the file they test: `foo.ts` → `foo.test.ts`.
- Integration and E2E tests go in a top-level `tests/` directory.

## Conventions
- Test description format: `it('should [expected behavior] when [condition]')`
- Each test must have a single, clear assertion goal.
- Mock all external dependencies (network, DB, filesystem).
- Do not commit tests with `.only` or `.skip` unless there is a documented reason.

## Coverage
- Aim for meaningful coverage, not 100% coverage for its own sake.
- All public-facing functions and API routes must have tests.
