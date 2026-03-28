# Skill: Security Review

> Auto-invoked workflow. Claude will trigger this skill automatically when security-sensitive code is detected.

## Trigger Conditions
- Code handling authentication or authorization.
- Code handling user input, environment variables, or secrets.
- Code making external HTTP requests.
- Database queries or raw SQL.

## Workflow Steps
1. Identify all attack surfaces in the code (injection, XSS, CSRF, broken auth, etc.).
2. Check for hardcoded secrets or credentials.
3. Verify input validation and sanitization.
4. Assess dependency risk (flag any unrecognized or outdated packages).
5. Produce a security report with severity ratings: **Critical / High / Medium / Low / Info**.
6. Suggest concrete remediations for all findings.
