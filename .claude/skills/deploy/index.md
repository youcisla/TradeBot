# Skill: Deploy

> Auto-invoked structured deployment checklist workflow.

## Pre-Deploy Checklist
- [ ] All tests pass locally.
- [ ] No uncommitted changes remain.
- [ ] Environment variables are validated for the target environment.
- [ ] Migrations have been reviewed and are safe to run.
- [ ] The changelog or release notes have been updated.

## Deploy Steps
1. Pull latest from the main branch.
2. Install dependencies cleanly.
3. Run the full test suite.
4. Build the production artifact.
5. Run database migrations (if applicable).
6. Deploy the artifact to the target environment.
7. Run smoke tests against the live environment.
8. Monitor error rates for 5 minutes post-deploy.

## Post-Deploy
- Tag the release in git.
- Notify the team of the deployment.
