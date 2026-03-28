# /deploy

Runs the deployment checklist and executes deployment steps.

## Behavior
- Confirm the target environment (staging / production) before proceeding.
- Run through the deployment checklist defined in `.claude/skills/deploy/`.
- Abort and report clearly if any step fails.
- Never deploy to production without explicit confirmation.

## Steps
1. Run tests — abort if any fail.
2. Build the project.
3. Validate environment variables.
4. Deploy to the confirmed target environment.
5. Run post-deploy smoke checks.
6. Report deployment status.
