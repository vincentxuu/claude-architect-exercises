---
paths:
  - "src/api/**/*"
  - "src/services/**/*"
---

# API Handler Conventions

- All handlers must be `async` functions
- Always wrap external calls in try/except
- Return structured error objects, never raise HTTP exceptions to callers
- Log errors with context: `logger.error("msg", extra={"request_id": ..., "user_id": ...})`
- Validate inputs at the boundary using Pydantic models
- Never return raw database objects — transform to response schemas first
