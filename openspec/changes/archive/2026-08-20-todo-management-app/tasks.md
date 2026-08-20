## 1. Project Setup

- [x] 1.1 Create the project layout from design.md §7 (`app/`, `alembic/`, `tests/`, `pyproject.toml` / `requirements.txt`).
- [x] 1.2 Add dependencies: `fastapi`, `uvicorn`, `sqlalchemy>=2`, `asyncpg`, `alembic`, `pydantic>=2`, `pydantic-settings`, `python-jose[cryptography]`, `passlib[bcrypt]`, `python-multipart`, `httpx` (tests).

## 2. Configuration & Database

- [x] 2.1 Implement `app/core/config.py` to load `DATABASE_URL`, `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRY_MINUTES` from environment; refuse to start if `JWT_SECRET` is missing.
- [x] 2.2 Implement `app/db/base.py` with async SQLAlchemy engine + `sessionmaker` + `DeclarativeBase`.
- [x] 2.3 Implement `app/db/models.py` with `User` and `Todo` ORM models matching TDD §3 (UUID PKs, varchar lengths, FK from `todos.user_id` → `users.id`, status enum values).

## 3. Migrations

- [x] 3.1 Initialize Alembic and configure `alembic.ini` / `env.py` to use `DATABASE_URL` and the SQLAlchemy `Base.metadata`.
- [x] 3.2 Generate `alembic/versions/0001_initial.py` creating `users` and `todos` with the columns from §3.
- [x] 3.3 Add the four indexes from §8: unique on `users.email`, indexes on `todos.user_id`, `todos.status`, `todos.due_date`.

## 4. Schemas & Security

- [x] 4.1 Implement `app/schemas/user.py` (Create / Read) and `app/schemas/todo.py` (Create / Update / Read) with the validation rules from §7 (title required + ≤200, priority 1–3, status enum, dueDate must be future).
- [x] 4.2 Implement `app/core/security.py`: bcrypt password hashing, JWT encode/decode, and a `get_current_user` dependency that decodes the bearer token and loads the user from the `sub` claim.

## 5. Repositories

- [x] 5.1 Implement `app/repositories/user_repo.py` with `get_by_email`, `get_by_id`, `create`.
- [x] 5.2 Implement `app/repositories/todo_repo.py` with `create`, `list_for_user(user_id, status, priority)`, `get_for_user(user_id, todo_id)`, `update_for_user(user_id, todo_id, fields)`, `delete_for_user(user_id, todo_id)` — all using parameterized `select()` / `delete()`.

## 6. Services

- [x] 6.1 Implement `app/services/todo_service.py` enforcing the business rules from §6: default `status = Pending`, due date cannot be in the past, and a `Completed` todo cannot revert to `Pending`. Raise domain exceptions that the API layer maps to 400/404.

## 7. API Layer

- [x] 7.1 Implement `app/api/deps.py` with `get_db` and `get_current_user`.
- [x] 7.2 Implement `app/api/v1/auth.py` with `POST /auth/register` (email/name/password) and `POST /auth/token` (OAuth2 password form → JWT) so the JWT auth requirement is end-to-end exercisable.
- [x] 7.3 Implement `app/api/v1/todos.py` with the five endpoints from §5: `POST /api/v1/todos`, `GET /api/v1/todos`, `GET /api/v1/todos/{id}`, `PUT /api/v1/todos/{id}`, `DELETE /api/v1/todos/{id}`, all returning the response shapes in §5 and all requiring the `get_current_user` dependency.
- [x] 7.4 Implement `app/main.py` to create the FastAPI app, mount the v1 router, and run with uvicorn.

## 8. Tests

- [x] 8.1 Set up `tests/conftest.py` with an async test DB session fixture and a client fixture that issues JWTs for test users.
- [x] 8.2 Add `tests/test_todos.py` covering every scenario in `specs/todos/spec.md`: create (happy + each validation rule), list (with/without filters + invalid filters), get-by-id (own, other-user → 404, unknown → 404), update (happy, validation, Completed→Pending rejected, other-user → 404), delete (own, other-user → 404, unknown → 404).
- [x] 8.3 Add `tests/test_auth.py` covering `specs/auth/spec.md`: missing token → 401, invalid token → 401, valid token → ok; listing returns only own todos; input validation rejects bad payloads before DB access.
- [ ] 8.4 Run the full test suite and confirm green.

  > Deferred to user: requires `pip install` + `pytest` in the local shell, which the
  > automated `Bash` tool could not execute during this session.

## 9. Verification

- [ ] 9.1 `openspec validate --change todo-management-app --strict` is green.

  > Deferred to user: `openspec` CLI not reachable from this session.

- [ ] 9.2 Start the service against a local Postgres, register a user, obtain a token, and exercise each of the five §5 endpoints via curl/HTTP client to confirm response shapes match the TDD examples.

  > Deferred to user: requires a running Postgres + `uvicorn`, runnable from the user's shell.
