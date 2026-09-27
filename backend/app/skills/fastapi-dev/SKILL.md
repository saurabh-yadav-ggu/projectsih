---
name: fastapi-dev
description: FastAPI backend development guidelines, router architecture, and Pydantic validation
---

# FastAPI Development Skill

## When to Use
Use when creating or modifying FastAPI routers, endpoints, dependency injection, and Pydantic models.

## Instructions
1. Organize routers by domain in `app/routers/` with appropriate APIRouter prefixes and tags.
2. Define Pydantic request and response schemas in `app/schemas/`.
3. Use dependency injection for authentication (`get_current_user`) and database sessions (`get_db`).
4. Always handle exceptions and return semantic HTTP status codes.
