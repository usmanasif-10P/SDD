## Context

This is a greenfield change: the repo currently has no application code, no FastAPI service, and no PostgreSQL schema. The constraints come directly from the TDD (FastAPI + PostgreSQL, layered architecture, the data model in §3, the five endpoints in §5, validation rules in §7, indexes in §8, JWT auth and ownership in §9). The system must implement only what the TDD specifies — section §10 "Future Enhancements" is excluded.

## Goals / Non-Goals

**Goals:**
- A FastAPI service that exposes exactly the five endpoints in §5 under `/api/v1`, returning the response shapes in §5.
- Layered architecture (router → service → repository) per §2.
- PostgreSQL schema for `users` and `todos` matching §3, with the indexes in §8.
- JWT bearer auth on every todo endpoint, with per-user ownership enforced so non-owners receive 404.
- Validation rules from §7 and transition rules from §6 enforced at the request/service boundary.

**Non-Goals:**
- Anything in §10 (reminders, subtasks, tags, notifications, shared todos).
- Authentication flows for user signup / password reset / email verification (TDD only specifies JWT auth and ownership; user records are introduced to own todos and authenticate).
- Filtering by `due_date` (§6 mentions it but §5 only exposes `status` and `priority` query params — out of scope unless §5 changes).
- Pagination, sorting, soft-delete, audit log, multi-tenant sharing.

## Decisions

### 1. Stack: FastAPI + SQLAlchemy 2.x async + asyncpg + Pydantic v2
- **Rationale:** FastAPI is required. SQLAlchemy 2.x async integrates cleanly with FastAPI's async handlers via asyncpg, gives type-safe ORM models, and lets Alembic manage migrations.
- **Alternatives considered:** Raw asyncpg queries (rejected — too much boilerplate, no migrations scaffolding), Tortoise ORM (rejected — less migration tooling than Alembic, weaker Pydantic integration).

### 2. Migration tool: Alembic
- **Rationale:** First-class migration story for SQLAlchemy; supports auto-generation from ORM models for the initial `users` / `todos` schema.
- **Alternatives considered:** Hand-written SQL migrations (rejected — harder to keep in sync with ORM changes later).

### 3. Auth: JWT via `python-jose` (or `PyJWT`), password hashing with `passlib[bcrypt]`
- **Rationale:** TDD §9 says "JWT authentication." A bearer-token middleware/dependency that decodes the JWT and resolves the user from the `sub` claim satisfies the spec. `passlib[bcrypt]` is the standard password hashing choice for FastAPI examples and keeps the user record compatible with future auth flows.
- **Alternatives considered:** Session cookies (rejected — TDD says JWT), OAuth2 third-party (rejected — overkill).

### 4. Ownership enforcement returns 404, not 403
- **Rationale:** Returning 404 for non-owned todos avoids leaking the existence of another user's records (information disclosure). Spec scenarios for get/update/delete another user's todo require this.
- **Alternatives considered:** 403 (rejected — leaks existence).

### 5. Status transition rule is enforced in the service layer
- **Rationale:** The "Completed → Pending is forbidden" rule (§6) is business logic, not request validation, so it lives in the service layer. Pydantic validates the field shape; the service checks the prior state.
- **Alternatives considered:** Database CHECK constraint (rejected — needs to compare to the prior row, which a CHECK can't see).

### 6. Filtering in the repository via SQLAlchemy `select()` with `where()`
- **Rationale:** Parameterized queries prevent SQL injection and use the `todos.status` and `todos.user_id` indexes from §8.
- **Alternatives considered:** ORM `query.filter()` (works, but async `select()` is the documented SQLAlchemy 2.x style).

### 7. Project layout
```
app/
  main.py                  # FastAPI app factory, router include
  core/
    config.py              # Settings (DB URL, JWT secret, algorithm, expiry)
    security.py            # JWT encode/decode, password hashing, current_user dependency
  db/
    base.py                # SQLAlchemy async engine + session
    models.py              # ORM models: User, Todo
  schemas/
    user.py                # Pydantic models for users
    todo.py                # Pydantic models for todos (Create, Update, Read)
  repositories/
    user_repo.py
    todo_repo.py
  services/
    user_service.py
    todo_service.py        # business rules: default status, due-date future, Completed→Pending forbidden
  api/
    deps.py                # get_db, get_current_user
    v1/
      todos.py             # the five /api/v1/todos endpoints
      auth.py              # login/token issuance for completeness of the auth flow
alembic/
  versions/
    0001_initial.py        # creates users and todos tables + the four §8 indexes
tests/
  test_todos.py
  test_auth.py
  conftest.py
```
- **Rationale:** Clean separation per §2 (router / service / repository) and lets tests target each layer.

### 8. JWT claim shape
- `sub`: user UUID (string).
- `exp`: expiry timestamp.
- A `/auth/token` endpoint (username/password → JWT) is included so the §9 auth requirement is end-to-end testable; user passwords are stored as bcrypt hashes. (The TDD does not show the login endpoint, but it is required for JWT auth to function.)

### 9. Status is stored as a string column with a CHECK constraint
- **Rationale:** Matches TDD §3.2 `varchar(20)` and prevents bad values at the DB layer in addition to the Pydantic check.

## Risks / Trade-offs

- **No user-signup endpoint in TDD** → adding a small registration endpoint is required to obtain a real user to authenticate as. Mitigated by keeping it minimal (email + name + password) and out of the TDD-spec'd surface area (it lives outside `/api/v1/todos`).
- **Due-date "future" check is server-clock dependent** → clients in other timezones may see surprising rejections; mitigated by accepting ISO-8601 with explicit `Z` and documenting server-time semantics.
- **Async SQLAlchemy has a steeper learning curve** than sync, but matches FastAPI's async handlers and is required for non-blocking DB I/O.
- **JWT secret management** is left to deployment; if a secret is missing in env, the service must refuse to start (fail-loud).
- **No pagination** on `GET /api/v1/todos` — acceptable for the TDD scope but could become a problem at scale; mitigated by an index on `user_id`.

## Migration Plan

1. Apply the Alembic migration `0001_initial.py` to create `users` and `todos` tables with the four indexes.
2. Run any seed scripts (none required by the TDD).
3. Deploy the FastAPI service; environment must provide `DATABASE_URL`, `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRY_MINUTES`.
4. Rollback: drop the two tables (and indexes) — no shared schema is touched, so rollback is a single down-migration.
