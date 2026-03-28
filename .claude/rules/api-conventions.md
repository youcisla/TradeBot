# API Design Conventions

> These rules define the standard patterns for all API endpoints in this project.

## REST Conventions
- Use plural nouns for resource names: `/users`, `/posts`.
- Use HTTP methods semantically: `GET` (read), `POST` (create), `PUT/PATCH` (update), `DELETE` (remove).
- Always version APIs: `/api/v1/...`

## Request & Response
- All request and response bodies must be JSON.
- Use consistent error response shape:
  ```json
  { "error": { "code": "ERROR_CODE", "message": "Human-readable message" } }
  ```
- Return appropriate HTTP status codes — never return 200 for an error.

## Auth
- All protected routes must validate the auth token before processing the request.
- Never expose internal error details or stack traces in API responses.
