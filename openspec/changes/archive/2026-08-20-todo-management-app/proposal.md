## Why

Users need a system to create, update, track, and delete their personal todo tasks with status tracking, due dates, and priorities. The current project lacks a todo management capability entirely, so we are introducing it from scratch as a FastAPI + PostgreSQL service.

## What Changes

- Add a new FastAPI web API for todo management with a layered architecture (FastAPI → Service → Repository → PostgreSQL).
- Persist users and todos in PostgreSQL using the data model defined in the TDD (Users and Todos tables, with status, priority, due date, timestamps).
- Expose the five REST endpoints defined in §5 of the TDD (`POST /api/v1/todos`, `GET /api/v1/todos`, `GET /api/v1/todos/{id}`, `PUT /api/v1/todos/{id}`, `DELETE /api/v1/todos/{id}`) under base URL `/api/v1`.
- Enforce the validation and business rules in §6 and §7 of the TDD: title required (≤200 chars), priority 1–3, status values `Pending` / `InProgress` / `Completed`, future-only `due_date`, completed tasks cannot revert to `Pending`, automatic `updated_at`.
- Apply the indexing strategy in §8 (unique index on `users.email`, indexes on `todos.user_id`, `todos.status`, `todos.due_date`).
- Filter list results by `status` and `priority` query parameters (the `due_date` filter is mentioned in §6 but not exposed in §5 query params — we keep filtering limited to what §5 specifies).
- Add JWT-based authentication and per-user authorization so users can only access their own todos (§9).

## Capabilities

### New Capabilities

- `todos`: Todo CRUD, status/priority/due-date fields, filtering by status and priority, validation rules, completion-state transition rules.
- `users`: User identity records (id, name, email, created_at) that own todos and authenticate via JWT.
- `auth`: JWT-based authentication and ownership checks that gate every todo operation to the authenticated user's own todos.

### Modified Capabilities

(none — this change introduces brand-new capabilities)

## Impact

- New FastAPI application bootstrapped from scratch with a layered (API / service / repository) structure.
- New PostgreSQL schema for `users` and `todos` with the indexes listed in §8.
- New Python dependencies: FastAPI, SQLAlchemy (or equivalent async DB layer), asyncpg/psycopg, Pydantic, a JWT library (`python-jose` or `PyJWT`), and a password hashing library (`passlib[bcrypt]` or `argon2-cffi`) for the user auth flow implied by §9.
- A Alembic (or equivalent) migration that creates both tables and their indexes.
- Items listed in §10 (task reminders, subtasks, tags, notifications, shared todos) are explicitly out of scope for this change.
