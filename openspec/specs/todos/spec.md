# todos Specification

## Purpose

Lets each authenticated user create, read, update, delete, and filter their own todo tasks with status tracking, priority, and optional due date, while enforcing the validation and transition rules defined in the TDD.

## Requirements

### Requirement: Create a todo
The system SHALL create a new todo owned by the authenticated user when a valid request body is posted to `POST /api/v1/todos`. The system MUST store `user_id` from the authenticated principal, MUST default `status` to `Pending` when the client omits it, MUST set `created_at` and `updated_at` to the server time, and MUST return the created todo in the response shape shown in §5.1 of the TDD.

#### Scenario: Create a todo with title, description, priority, and due date
- **WHEN** the authenticated user posts `{"title": "Prepare Architecture Document", "description": "Write TDD for Todo system", "priority": 3, "dueDate": "<future ISO timestamp>"}` to `POST /api/v1/todos`
- **THEN** the system persists a new todo with `status = "Pending"`, `user_id` from the JWT subject, the supplied `title`, `description`, `priority`, and `dueDate`, and returns the created todo with `id`, `title`, `status`, `priority`, `dueDate`, and `createdAt` per the §5.1 response shape

#### Scenario: Reject a todo with an empty or missing title
- **WHEN** the request body is missing `title` or `title` is an empty string
- **THEN** the system MUST reject the request with a validation error and MUST NOT create a todo

#### Scenario: Reject a todo whose title exceeds 200 characters
- **WHEN** the request body has `title` longer than 200 characters
- **THEN** the system MUST reject the request with a validation error and MUST NOT create a todo

#### Scenario: Reject a todo with priority outside 1–3
- **WHEN** the request body has `priority` outside the inclusive range 1–3
- **THEN** the system MUST reject the request with a validation error and MUST NOT create a todo

#### Scenario: Reject a todo with a due date in the past
- **WHEN** the request body has `dueDate` earlier than the current server time
- **THEN** the system MUST reject the request with a validation error and MUST NOT create a todo

### Requirement: List todos
The system SHALL return todos belonging only to the authenticated user from `GET /api/v1/todos`. The system MUST support filtering by `status` and `priority` query parameters (each optional), MUST restrict `status` filter values to `Pending` / `InProgress` / `Completed`, and MUST restrict `priority` filter values to 1–3. When both filters are supplied, the system MUST return only todos matching both. Each returned item MUST match the §5.2 response shape.

#### Scenario: List all own todos when no filter is supplied
- **WHEN** the authenticated user calls `GET /api/v1/todos` with no query parameters
- **THEN** the system returns todos owned only by that user in the §5.2 response shape

#### Scenario: Filter by status
- **WHEN** the authenticated user calls `GET /api/v1/todos?status=Pending`
- **THEN** the system returns only own todos whose status equals `Pending`

#### Scenario: Filter by priority
- **WHEN** the authenticated user calls `GET /api/v1/todos?priority=3`
- **THEN** the system returns only own todos whose priority equals 3

#### Scenario: Reject invalid status filter
- **WHEN** the authenticated user calls `GET /api/v1/todos?status=Done`
- **THEN** the system MUST reject the request with a validation error

#### Scenario: Reject invalid priority filter
- **WHEN** the authenticated user calls `GET /api/v1/todos?priority=5`
- **THEN** the system MUST reject the request with a validation error

### Requirement: Get a todo by id
The system SHALL return the todo identified by `{id}` from `GET /api/v1/todos/{id}` only when the todo belongs to the authenticated user. The response MUST match the §5.3 response shape.

#### Scenario: Get own todo by id
- **WHEN** the authenticated user calls `GET /api/v1/todos/{id}` for a todo they own
- **THEN** the system returns the todo in the §5.3 response shape

#### Scenario: Reject fetching another user's todo
- **WHEN** the authenticated user calls `GET /api/v1/todos/{id}` for a todo they do not own
- **THEN** the system MUST respond with 404 (the todo must appear non-existent to non-owners)

#### Scenario: Return 404 for an unknown todo id
- **WHEN** the authenticated user calls `GET /api/v1/todos/{id}` for an id that does not exist
- **THEN** the system MUST respond with 404

### Requirement: Update a todo
The system SHALL update fields of a todo owned by the authenticated user when `PUT /api/v1/todos/{id}` is called. The system MUST validate any provided fields against the same rules as creation (title length, priority range, due date in future, status allowed values), MUST automatically refresh `updated_at` on every successful update, and MUST reject attempts to change the `status` of a `Completed` todo to `Pending`. On success the system MUST return `{"message": "Todo updated successfully"}` per §5.4.

#### Scenario: Update title, status, and priority
- **WHEN** the authenticated user calls `PUT /api/v1/todos/{id}` with `{"title": "Prepare Architecture Document", "status": "InProgress", "priority": 3}` for an own todo
- **THEN** the system updates the fields, refreshes `updated_at`, and returns `{"message": "Todo updated successfully"}`

#### Scenario: Reject invalid fields on update
- **WHEN** the authenticated user calls `PUT /api/v1/todos/{id}` with `title` longer than 200 characters, `priority` outside 1–3, an invalid `status` value, or a `dueDate` in the past
- **THEN** the system MUST reject the request with a validation error and MUST NOT modify the todo

#### Scenario: Reject reverting a Completed todo to Pending
- **WHEN** the authenticated user calls `PUT /api/v1/todos/{id}` with `status: "Pending"` on a todo whose current `status` is `Completed`
- **THEN** the system MUST reject the request with a transition error and MUST NOT change the todo's status

#### Scenario: Reject updating another user's todo
- **WHEN** the authenticated user calls `PUT /api/v1/todos/{id}` for a todo they do not own
- **THEN** the system MUST respond with 404 and MUST NOT modify any todo

### Requirement: Delete a todo
The system SHALL delete a todo owned by the authenticated user when `DELETE /api/v1/todos/{id}` is called. On success the system MUST return `{"message": "Todo deleted successfully"}` per §5.5.

#### Scenario: Delete own todo
- **WHEN** the authenticated user calls `DELETE /api/v1/todos/{id}` for a todo they own
- **THEN** the system deletes the todo and returns `{"message": "Todo deleted successfully"}`

#### Scenario: Reject deleting another user's todo
- **WHEN** the authenticated user calls `DELETE /api/v1/todos/{id}` for a todo they do not own
- **THEN** the system MUST respond with 404 and MUST NOT delete any todo

#### Scenario: Delete of an unknown id
- **WHEN** the authenticated user calls `DELETE /api/v1/todos/{id}` for an id that does not exist
- **THEN** the system MUST respond with 404

### Requirement: Todo status values
The system SHALL only accept `Pending`, `InProgress`, and `Completed` as valid values for `status`. The system MUST persist status as a string column matching those values.

#### Scenario: Default status on creation
- **WHEN** a todo is created without an explicit `status`
- **THEN** the system MUST persist `status = "Pending"`

#### Scenario: Reject an unknown status value
- **WHEN** a create or update request includes a `status` value outside `Pending` / `InProgress` / `Completed`
- **THEN** the system MUST reject the request with a validation error

### Requirement: Todo indexes
The system SHALL create the indexes defined in §8 of the TDD: a unique index on `users.email`, an index on `todos.user_id`, an index on `todos.status`, and an index on `todos.due_date`.

#### Scenario: Indexes exist after migration
- **WHEN** the database migration is applied
- **THEN** the four indexes named above exist on the corresponding tables
