# auth Specification

## Purpose

Authenticates users with JWTs and enforces ownership so that every todo operation is performed by, and scoped to, the authenticated user.

## Requirements

### Requirement: JWT authentication on todo endpoints
The system SHALL require a valid JWT bearer token on every endpoint under `/api/v1/todos`. Requests without a valid token MUST be rejected with 401. The JWT subject MUST identify the user whose todos the request acts on.

#### Scenario: Request without a token
- **WHEN** a client calls any `/api/v1/todos` endpoint without an `Authorization` header
- **THEN** the system MUST respond with 401 and MUST NOT execute the request

#### Scenario: Request with an invalid or expired token
- **WHEN** a client calls any `/api/v1/todos` endpoint with a malformed, signature-invalid, or expired JWT
- **THEN** the system MUST respond with 401 and MUST NOT execute the request

#### Scenario: Request with a valid token
- **WHEN** a client calls any `/api/v1/todos` endpoint with a valid JWT
- **THEN** the system MUST identify the user from the token's subject and execute the request scoped to that user

### Requirement: Per-user authorization for todos
The system SHALL ensure that an authenticated user can only read, update, or delete their own todos. Any attempt by a user to access a todo whose `user_id` does not match the authenticated subject MUST be rejected as if the todo did not exist (404).

#### Scenario: Get another user's todo is hidden
- **WHEN** an authenticated user calls `GET /api/v1/todos/{id}` for a todo owned by a different user
- **THEN** the system MUST respond with 404

#### Scenario: Update another user's todo is rejected
- **WHEN** an authenticated user calls `PUT /api/v1/todos/{id}` for a todo owned by a different user
- **THEN** the system MUST respond with 404 and MUST NOT modify any todo

#### Scenario: Delete another user's todo is rejected
- **WHEN** an authenticated user calls `DELETE /api/v1/todos/{id}` for a todo owned by a different user
- **THEN** the system MUST respond with 404 and MUST NOT delete any todo

#### Scenario: Listing returns only own todos
- **WHEN** an authenticated user calls `GET /api/v1/todos` (with or without filters)
- **THEN** the system MUST return only todos owned by the authenticated user

### Requirement: Input validation prevents injection
The system MUST validate and parameterize all inputs (request bodies, query parameters, and path parameters) and MUST NOT construct SQL by concatenating user input. Inputs that fail validation MUST be rejected with 400 before any database operation.

#### Scenario: Invalid input rejected before DB access
- **WHEN** a request body, query parameter, or path parameter fails validation
- **THEN** the system MUST respond with 400 and MUST NOT issue a database query for that operation
